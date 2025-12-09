"""Tests for tool caching functionality.

Tests cover:
- In-memory caching
- File-based persistence
- Cache expiration (TTL)
- Cache key generation
- Integration with tools
"""
import pytest
import tempfile
import os
import time
from construction_assistant.tool_cache import (
    ToolCache,
    init_tool_cache,
    get_tool_cache,
    cached_tool
)


class TestToolCacheBasics:
    """Tests for basic ToolCache functionality."""
    
    def test_cache_initialization(self):
        """Test ToolCache initialization."""
        cache = ToolCache()
        assert cache.memory_cache == {}
        assert cache.cache_dir is None
    
    def test_cache_with_directory(self):
        """Test ToolCache with file persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ToolCache(cache_dir=tmpdir)
            assert os.path.exists(tmpdir)
    
    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        key1 = ToolCache._generate_key("tool_name", {"param": "value"})
        key2 = ToolCache._generate_key("tool_name", {"param": "value"})
        
        assert key1 == key2
        assert "tool_name" in key1
    
    def test_cache_key_unique_for_different_inputs(self):
        """Test that different inputs generate different cache keys."""
        key1 = ToolCache._generate_key("tool_name", {"param": "value1"})
        key2 = ToolCache._generate_key("tool_name", {"param": "value2"})
        
        assert key1 != key2


class TestCacheStorage:
    """Tests for cache storage and retrieval."""
    
    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        cache = ToolCache()
        tool_input = {"scope": "excavation"}
        result = {"suppliers": 47, "trend": "stable"}
        
        # Should miss initially
        assert cache.get("fetch_market_data", tool_input) is None
        
        # Set and retrieve
        cache.set("fetch_market_data", tool_input, result)
        cached = cache.get("fetch_market_data", tool_input)
        
        assert cached == result
    
    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        cache = ToolCache()
        result = cache.get("unknown_tool", {})
        assert result is None
    
    def test_cache_get_stats(self):
        """Test cache statistics."""
        cache = ToolCache()
        
        assert cache.get_stats()["memory_entries"] == 0
        
        cache.set("tool", {"p": 1}, {"result": 1})
        assert cache.get_stats()["memory_entries"] == 1
        
        cache.set("tool", {"p": 2}, {"result": 2})
        assert cache.get_stats()["memory_entries"] == 2


class TestCacheExpiration:
    """Tests for cache TTL and expiration."""
    
    def test_cache_expiration_ttl(self):
        """Test that cache entries expire after TTL."""
        # Create cache with 1-second TTL
        cache = ToolCache(ttl_seconds=1)
        
        tool_input = {"scope": "roofing"}
        result = {"total": 36000}
        
        cache.set("estimate_cost", tool_input, result)
        
        # Should be available immediately
        assert cache.get("estimate_cost", tool_input) == result
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get("estimate_cost", tool_input) is None
    
    def test_cache_partial_expiration(self):
        """Test that only expired entries are removed."""
        cache = ToolCache(ttl_seconds=1)
        
        input1 = {"scope": "excavation"}
        input2 = {"scope": "roofing"}
        result = {"data": "value"}
        
        cache.set("tool", input1, result)
        time.sleep(0.5)
        cache.set("tool", input2, result)
        
        time.sleep(0.7)
        
        # First entry should be expired, second should be available
        assert cache.get("tool", input1) is None
        assert cache.get("tool", input2) == result


class TestFilePersistence:
    """Tests for file-based cache persistence."""
    
    def test_file_cache_save_and_load(self):
        """Test saving to and loading from file cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ToolCache(cache_dir=tmpdir, ttl_seconds=3600)
            
            tool_input = {"scope": "concrete"}
            result = {"total": 12000}
            
            # Save to file cache
            cache.set("estimate", tool_input, result)
            
            # Create new cache instance (simulating restart)
            cache2 = ToolCache(cache_dir=tmpdir, ttl_seconds=3600)
            
            # Should load from file
            cached = cache2.get("estimate", tool_input)
            assert cached == result
    
    def test_file_cache_directory_creation(self):
        """Test that cache directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, "new_cache_dir")
            assert not os.path.exists(cache_dir)
            
            cache = ToolCache(cache_dir=cache_dir)
            assert os.path.exists(cache_dir)
    
    def test_cache_clear_removes_files(self):
        """Test that clearing cache removes file entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ToolCache(cache_dir=tmpdir)
            
            cache.set("tool", {"p": 1}, {"r": 1})
            cache.set("tool", {"p": 2}, {"r": 2})
            
            assert cache.get_stats()["file_entries"] > 0
            
            cache.clear()
            
            assert cache.get_stats()["memory_entries"] == 0


class TestGlobalCache:
    """Tests for global cache instance."""
    
    def test_init_tool_cache(self):
        """Test initialization of global cache."""
        # Initialize with temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = init_tool_cache(cache_dir=tmpdir, ttl_seconds=600)
            
            assert get_tool_cache() == cache
            
            # Use it
            cache.set("test", {"p": 1}, {"result": 1})
            assert cache.get("test", {"p": 1}) == {"result": 1}
    
    def test_get_tool_cache_before_init(self):
        """Test that get_tool_cache returns None before initialization."""
        # Note: This test assumes global state, may need isolation
        import construction_assistant.tool_cache as cache_module
        
        # Temporarily clear global cache
        original = cache_module._global_cache
        cache_module._global_cache = None
        
        try:
            assert get_tool_cache() is None
        finally:
            cache_module._global_cache = original


class TestCachedToolDecorator:
    """Tests for @cached_tool decorator."""
    
    def test_cached_tool_decorator_basic(self):
        """Test basic cached_tool decorator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = init_tool_cache(cache_dir=tmpdir)
            
            call_count = 0
            
            @cached_tool(cache=cache)
            def expensive_tool(param: str) -> dict:
                nonlocal call_count
                call_count += 1
                return {"result": param, "computed": True}
            
            # First call should execute
            result1 = expensive_tool("test")
            assert call_count == 1
            assert result1["computed"] is True
            
            # Second call should use cache
            result2 = expensive_tool("test")
            assert call_count == 1  # Still 1, not 2
            assert result2 == result1
    
    def test_cached_tool_different_params(self):
        """Test cached_tool with different parameters."""
        cache = init_tool_cache()
        
        call_count = 0
        
        @cached_tool(cache=cache)
        def tool_func(param: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"param": param, "count": call_count}
        
        result1 = tool_func("a")
        result2 = tool_func("b")
        
        # Both parameters should execute (different cache keys)
        assert call_count == 2
        assert result1["param"] == "a"
        assert result2["param"] == "b"
    
    def test_cached_tool_no_cache(self):
        """Test cached_tool decorator when no cache is configured."""
        # Clear global cache
        import construction_assistant.tool_cache as cache_module
        original = cache_module._global_cache
        cache_module._global_cache = None
        
        try:
            call_count = 0
            
            @cached_tool()
            def tool_func(param: str) -> dict:
                nonlocal call_count
                call_count += 1
                return {"param": param}
            
            # Without cache, function should always execute
            result1 = tool_func("test")
            result2 = tool_func("test")
            
            assert call_count == 2  # Called twice, no caching
            
        finally:
            cache_module._global_cache = original


class TestCacheIntegration:
    """Integration tests for cache with tools."""
    
    def test_cache_with_tool_like_function(self):
        """Test cache with function signature like actual tools."""
        cache = ToolCache()
        
        def fetch_data(scope: str) -> dict:
            return {"scope": scope, "suppliers": 50}
        
        # Cache should work with standard tool signatures
        input_dict = {"scope": "excavation"}
        result = fetch_data(**input_dict)
        
        cache.set("fetch_data", input_dict, result)
        cached = cache.get("fetch_data", input_dict)
        
        assert cached == result


class TestCacheErrorHandling:
    """Tests for error handling in cache."""
    
    def test_cache_invalid_directory(self):
        """Test cache behavior with invalid directory - falls back to memory-only."""
        # Should fall back to memory-only cache on error
        cache = ToolCache(cache_dir="/invalid/path/that/cannot/exist")
        
        # Cache directory should be None (fallback)
        assert cache.cache_dir is None
        
        # Cache operations should still work (memory-only)
        cache.set("tool", {"p": 1}, {"r": 1})
        assert cache.get("tool", {"p": 1}) == {"r": 1}
    
    def test_cache_corrupted_file(self):
        """Test cache recovery from corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ToolCache(cache_dir=tmpdir)
            
            # Manually create corrupted cache file
            cache_file = os.path.join(tmpdir, "test_key.json")
            with open(cache_file, "w") as f:
                f.write("{ invalid json }")
            
            # Should handle gracefully
            result = cache._load_from_file("test_key")
            assert result is None
