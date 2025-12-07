"""Tests for parallel tool execution.

Tests cover:
- Sequential fallback for single tools
- Parallel execution with multiple tools
- Error handling in parallel execution
- AsyncIO vs ThreadPoolExecutor modes
"""
import pytest
import time
from construction_assistant.parallel_executor import (
    ParallelToolExecutor,
    create_parallel_executor
)


class TestParallelToolExecutor:
    """Tests for ParallelToolExecutor."""
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        executor = ParallelToolExecutor(max_workers=4)
        assert executor.max_workers == 4
        assert executor.use_asyncio is True
    
    def test_executor_with_thread_mode(self):
        """Test executor in thread mode."""
        executor = ParallelToolExecutor(max_workers=4, use_asyncio=False)
        assert executor.use_asyncio is False
        assert executor.executor is not None
    
    def test_executor_context_manager(self):
        """Test executor as context manager."""
        with create_parallel_executor() as executor:
            assert executor is not None
    
    def test_execute_single_tool(self):
        """Test execution of single tool."""
        executor = ParallelToolExecutor()
        
        def mock_invoke(tool_name, tool_input):
            return {"tool": tool_name, "input": tool_input}
        
        tool_calls = [
            {"id": "call-1", "tool": "fetch_data", "tool_input": {"scope": "excavation"}}
        ]
        
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        
        assert "call-1" in results
        assert results["call-1"]["tool"] == "fetch_data"
    
    def test_execute_multiple_tools_parallel(self):
        """Test parallel execution of multiple tools."""
        executor = ParallelToolExecutor(max_workers=4, use_asyncio=False)
        
        execution_times = []
        
        def mock_invoke(tool_name, tool_input):
            start = time.time()
            time.sleep(0.1)  # Simulate work
            execution_times.append(time.time() - start)
            return {"tool": tool_name, "result": "success"}
        
        tool_calls = [
            {"id": f"call-{i}", "tool": f"tool_{i}", "tool_input": {"p": i}}
            for i in range(3)
        ]
        
        start_time = time.time()
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        total_time = time.time() - start_time
        
        # All tools should complete
        assert len(results) == 3
        for i in range(3):
            assert f"call-{i}" in results
            assert results[f"call-{i}"]["tool"] == f"tool_{i}"
        
        # Parallel execution should be faster than sequential
        # Sequential would be ~0.3s, parallel should be ~0.1s + overhead
        assert total_time < 0.3, f"Execution took {total_time}s, expected ~0.1s for parallel"
    
    def test_execute_empty_tool_calls(self):
        """Test execution with empty tool calls list."""
        executor = ParallelToolExecutor()
        
        def mock_invoke(tool_name, tool_input):
            return {}
        
        results = executor.execute_tools_parallel([], mock_invoke)
        assert results == {}
    
    def test_tool_call_error_handling(self):
        """Test error handling in tool execution."""
        executor = ParallelToolExecutor(use_asyncio=False)
        
        def mock_invoke(tool_name, tool_input):
            if "fail" in tool_name:
                raise Exception(f"Tool {tool_name} failed")
            return {"result": "success"}
        
        tool_calls = [
            {"id": "call-1", "tool": "success_tool", "tool_input": {}},
            {"id": "call-2", "tool": "fail_tool", "tool_input": {}},
            {"id": "call-3", "tool": "success_tool", "tool_input": {}},
        ]
        
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        
        # All should have results
        assert "call-1" in results
        assert "call-2" in results
        assert "call-3" in results
        
        # Failed tool should have error
        assert "error" in results["call-2"]
        
        # Successful tools should not
        assert "result" in results["call-1"]
        assert "result" in results["call-3"]
    
    def test_tool_call_format_variations(self):
        """Test handling different tool call formats."""
        executor = ParallelToolExecutor(use_asyncio=False)
        
        def mock_invoke(tool_name, tool_input):
            return {"tool": tool_name}
        
        # Mix of 'tool' vs 'name', 'tool_input' vs 'input'
        tool_calls = [
            {"id": "call-1", "tool": "tool_a", "tool_input": {}},
            {"id": "call-2", "name": "tool_b", "input": {}},
        ]
        
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        
        assert len(results) == 2
        assert "call-1" in results
        assert "call-2" in results


class TestExecutorModes:
    """Tests for different executor modes."""
    
    def test_threadpool_executor_mode(self):
        """Test ThreadPoolExecutor mode."""
        executor = ParallelToolExecutor(max_workers=2, use_asyncio=False)
        
        call_order = []
        
        def mock_invoke(tool_name, tool_input):
            call_order.append(tool_name)
            time.sleep(0.05)
            return {"executed": tool_name}
        
        tool_calls = [
            {"id": f"call-{i}", "tool": f"tool_{i}", "tool_input": {}}
            for i in range(3)
        ]
        
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        
        # All should execute
        assert len(results) == 3
        # Order might vary due to parallelization
        assert set(call_order) == {"tool_0", "tool_1", "tool_2"}
    
    def test_asyncio_executor_fallback(self):
        """Test fallback from asyncio to threading."""
        # Create with asyncio, but it will fall back if needed
        executor = ParallelToolExecutor(max_workers=2, use_asyncio=True)
        
        def mock_invoke(tool_name, tool_input):
            return {"tool": tool_name, "success": True}
        
        tool_calls = [
            {"id": "call-1", "tool": "tool_a", "tool_input": {}},
            {"id": "call-2", "tool": "tool_b", "tool_input": {}},
        ]
        
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        
        # Should execute successfully (may use fallback)
        assert len(results) == 2
        assert all("tool" in v for v in results.values())


class TestExecutorPerformance:
    """Tests for executor performance characteristics."""
    
    def test_parallel_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential."""
        executor = ParallelToolExecutor(max_workers=3, use_asyncio=False)
        
        def mock_invoke(tool_name, tool_input):
            time.sleep(0.05)
            return {"result": tool_name}
        
        tool_calls = [
            {"id": f"call-{i}", "tool": f"tool_{i}", "tool_input": {}}
            for i in range(3)
        ]
        
        start = time.time()
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        parallel_time = time.time() - start
        
        # Sequential would take ~0.15s (3 * 0.05), parallel should be ~0.05s + overhead
        sequential_time = 3 * 0.05
        
        # Parallel should be significantly faster (at least 30% faster)
        assert parallel_time < sequential_time * 0.7, \
            f"Parallel ({parallel_time:.3f}s) not faster than sequential ({sequential_time:.3f}s)"
    
    def test_overhead_for_single_tool(self):
        """Test that single tool has minimal overhead."""
        executor = ParallelToolExecutor(use_asyncio=False)
        
        def mock_invoke(tool_name, tool_input):
            return {"result": "success"}
        
        tool_calls = [
            {"id": "call-1", "tool": "tool_a", "tool_input": {}}
        ]
        
        # Single tool should execute quickly
        start = time.time()
        results = executor.execute_tools_parallel(tool_calls, mock_invoke)
        elapsed = time.time() - start
        
        assert len(results) == 1
        # Should be very fast (< 100ms even with overhead)
        assert elapsed < 0.1


class TestExecutorShutdown:
    """Tests for executor cleanup."""
    
    def test_executor_shutdown_threaded(self):
        """Test executor shutdown with ThreadPoolExecutor."""
        executor = ParallelToolExecutor(use_asyncio=False)
        
        # Should not raise
        executor.shutdown()
        
        # Can be called multiple times
        executor.shutdown()
    
    def test_context_manager_cleanup(self):
        """Test context manager cleanup."""
        def mock_invoke(tool_name, tool_input):
            return {"result": "success"}
        
        with ParallelToolExecutor(use_asyncio=False) as executor:
            tool_calls = [{"id": "call-1", "tool": "tool_a", "tool_input": {}}]
            results = executor.execute_tools_parallel(tool_calls, mock_invoke)
            assert len(results) == 1
        
        # Should be cleaned up after context


class TestCreateParallelExecutor:
    """Tests for factory function."""
    
    def test_create_with_defaults(self):
        """Test creating executor with defaults."""
        executor = create_parallel_executor()
        assert executor.max_workers == 4
        assert executor.use_asyncio is True
    
    def test_create_with_custom_params(self):
        """Test creating executor with custom parameters."""
        executor = create_parallel_executor(max_workers=8, use_asyncio=False)
        assert executor.max_workers == 8
        assert executor.use_asyncio is False
    
    def test_create_returns_executor(self):
        """Test that factory returns proper executor."""
        executor = create_parallel_executor()
        assert isinstance(executor, ParallelToolExecutor)
