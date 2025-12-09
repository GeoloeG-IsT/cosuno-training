"""Caching layer for tool execution results.

This module provides:
- In-memory caching with TTL
- File-based persistent cache (optional)
- Cache key generation from tool name + arguments
- Decorator pattern for easy tool caching
"""
import hashlib
import json
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ToolCache:
    """In-memory cache for tool results with optional persistence."""
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_seconds: int = 3600):
        """Initialize the tool cache.
        
        Args:
            cache_dir: Optional directory for persistent cache files.
                      If None, cache is memory-only.
            ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
        """
        self.memory_cache: Dict[str, dict] = {}
        self.cache_dir = cache_dir
        self.ttl = timedelta(seconds=ttl_seconds)
        
        if cache_dir:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                logger.info(f"Created cache directory: {cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to create cache directory {cache_dir}: {str(e)}. Using memory-only cache.")
                self.cache_dir = None
    
    @staticmethod
    def _generate_key(tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Generate a cache key from tool name and inputs.
        
        Uses SHA256 hash of JSON-serialized input for consistent, short keys.
        """
        # Sort dict keys for consistent hashing
        sorted_input = json.dumps(tool_input, sort_keys=True, default=str)
        input_hash = hashlib.sha256(sorted_input.encode()).hexdigest()[:8]
        return f"{tool_name}_{input_hash}"
    
    def get(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[Any]:
        """Get a cached tool result if available and not expired.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input dict passed to the tool
            
        Returns:
            Cached result if found and valid, None otherwise
        """
        key = self._generate_key(tool_name, tool_input)
        
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if datetime.now() < entry["expires_at"]:
                logger.info(f"✅ Cache HIT for {tool_name} (key: {key})")
                return entry["result"]
            else:
                logger.info(f"⏰ Cache EXPIRED for {tool_name} (key: {key})")
                del self.memory_cache[key]
        
        # Check file cache if available
        if self.cache_dir:
            cached_result = self._load_from_file(key)
            if cached_result is not None:
                logger.info(f"✅ Cache HIT (file) for {tool_name} (key: {key})")
                # Reload into memory cache
                self.memory_cache[key] = {
                    "result": cached_result,
                    "expires_at": datetime.now() + self.ttl
                }
                return cached_result
        
        logger.debug(f"❌ Cache MISS for {tool_name} (key: {key})")
        return None
    
    def set(self, tool_name: str, tool_input: Dict[str, Any], result: Any) -> None:
        """Cache a tool result.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input dict that was passed to the tool
            result: Result to cache
        """
        key = self._generate_key(tool_name, tool_input)
        
        # Store in memory cache
        self.memory_cache[key] = {
            "result": result,
            "expires_at": datetime.now() + self.ttl
        }
        
        # Store in file cache if configured
        if self.cache_dir:
            self._save_to_file(key, result)
        
        logger.info(f"💾 Cached result for {tool_name} (key: {key}, TTL: {self.ttl.total_seconds()}s)")
    
    def _load_from_file(self, key: str) -> Optional[Any]:
        """Load a cached result from file."""
        if not self.cache_dir:
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    expires_at = datetime.fromisoformat(data.get("expires_at"))
                    if datetime.now() < expires_at:
                        return data.get("result")
                    else:
                        os.remove(cache_file)  # Remove expired file
        except Exception as e:
            logger.warning(f"Error loading file cache for {key}: {str(e)}")
        
        return None
    
    def _save_to_file(self, key: str, result: Any) -> None:
        """Save a cached result to file."""
        if not self.cache_dir:
            return
        
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            data = {
                "result": result,
                "expires_at": (datetime.now() + self.ttl).isoformat(),
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Error saving file cache for {key}: {str(e)}")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.memory_cache.clear()
        if self.cache_dir:
            import shutil
            try:
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
                logger.info(f"Cleared cache directory: {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Error clearing file cache: {str(e)}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "memory_entries": len(self.memory_cache),
            "file_entries": (
                len([f for f in os.listdir(self.cache_dir) if f.endswith(".json")])
                if self.cache_dir and os.path.exists(self.cache_dir)
                else 0
            )
        }


# Global cache instance (can be customized)
_global_cache: Optional[ToolCache] = None


def init_tool_cache(cache_dir: Optional[str] = None, ttl_seconds: int = 3600) -> ToolCache:
    """Initialize the global tool cache.
    
    Args:
        cache_dir: Optional directory for persistent cache
        ttl_seconds: Time-to-live for cache entries
        
    Returns:
        The initialized ToolCache instance
    """
    global _global_cache
    _global_cache = ToolCache(cache_dir=cache_dir, ttl_seconds=ttl_seconds)
    return _global_cache


def get_tool_cache() -> Optional[ToolCache]:
    """Get the global tool cache instance."""
    return _global_cache


def cached_tool(cache: Optional[ToolCache] = None) -> Callable:
    """Decorator to cache tool results.
    
    Usage:
        @cached_tool()
        def my_expensive_tool(param1, param2) -> dict:
            # expensive computation
            return result
    
    Args:
        cache: Optional ToolCache instance. If None, uses global cache.
    
    Returns:
        Decorated function that caches results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Use provided cache or global cache
            tool_cache = cache or _global_cache
            
            if not tool_cache:
                logger.debug(f"No cache configured for {func.__name__}, executing without caching")
                return func(*args, **kwargs)
            
            # Convert args and kwargs to a dict for cache key generation
            # This assumes the function takes a single dict argument or keyword arguments
            if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                tool_input = args[0]
            else:
                # Convert args and kwargs to dict
                import inspect
                sig = inspect.signature(func)
                tool_input = sig.bind(*args, **kwargs).arguments
            
            # Check cache
            cached_result = tool_cache.get(func.__name__, tool_input)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            tool_cache.set(func.__name__, tool_input, result)
            
            return result
        
        return wrapper
    
    return decorator
