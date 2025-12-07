"""Parallel tool execution support for construction agent.

Provides:
- Concurrent execution of independent tools
- Asyncio-based parallel invocation
- Fallback to sequential execution if needed
- Result aggregation and error handling
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ParallelToolExecutor:
    """Executes tools in parallel when possible."""
    
    def __init__(self, max_workers: int = 4, use_asyncio: bool = True):
        """Initialize the parallel executor.
        
        Args:
            max_workers: Maximum number of concurrent workers
            use_asyncio: If True, use asyncio for concurrency. If False, use ThreadPoolExecutor.
        """
        self.max_workers = max_workers
        self.use_asyncio = use_asyncio
        self.executor = None
        
        if not use_asyncio:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_invoke_fn,
    ) -> Dict[str, Any]:
        """Execute multiple tool calls in parallel.
        
        Args:
            tool_calls: List of tool call dicts with 'tool', 'tool_input', 'id'
            tool_invoke_fn: Function to invoke a tool: fn(tool_name, tool_input) -> result
            
        Returns:
            Dict mapping tool_id -> result
        """
        if not tool_calls:
            return {}
        
        if len(tool_calls) == 1:
            # Single tool, no parallelization needed
            return self._execute_single_tool(tool_calls[0], tool_invoke_fn)
        
        if self.use_asyncio:
            try:
                # Try to use asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # Can't use asyncio in running loop, fall back to threads
                    return self._execute_tools_threaded(tool_calls, tool_invoke_fn)
                except RuntimeError:
                    # No running loop, we can create one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            self._execute_tools_async(tool_calls, tool_invoke_fn)
                        )
                    finally:
                        loop.close()
            except Exception as e:
                logger.warning(f"Asyncio execution failed: {str(e)}. Falling back to threaded.")
                return self._execute_tools_threaded(tool_calls, tool_invoke_fn)
        else:
            return self._execute_tools_threaded(tool_calls, tool_invoke_fn)
    
    async def _execute_tools_async(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_invoke_fn,
    ) -> Dict[str, Any]:
        """Execute tools concurrently using asyncio."""
        tasks = []
        
        for tool_call in tool_calls:
            task = asyncio.create_task(
                self._invoke_tool_async(tool_call, tool_invoke_fn)
            )
            tasks.append((tool_call.get("id"), task))
        
        results = {}
        for tool_id, task in tasks:
            try:
                result = await task
                results[tool_id] = result
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_id}: {str(e)}")
                results[tool_id] = {"error": str(e)}
        
        return results
    
    async def _invoke_tool_async(self, tool_call: Dict[str, Any], tool_invoke_fn) -> Any:
        """Invoke a single tool asynchronously."""
        tool_name = tool_call.get("tool") or tool_call.get("name")
        tool_input = tool_call.get("tool_input") or tool_call.get("input", {})
        
        # Run blocking operation in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            tool_invoke_fn,
            tool_name,
            tool_input
        )
    
    def _execute_tools_threaded(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_invoke_fn,
    ) -> Dict[str, Any]:
        """Execute tools concurrently using ThreadPoolExecutor."""
        results = {}
        futures = {}
        
        # Submit all tools
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for tool_call in tool_calls:
                tool_id = tool_call.get("id")
                tool_name = tool_call.get("tool") or tool_call.get("name")
                tool_input = tool_call.get("tool_input") or tool_call.get("input", {})
                
                future = executor.submit(tool_invoke_fn, tool_name, tool_input)
                futures[future] = tool_id
            
            # Collect results as they complete
            for future in as_completed(futures):
                tool_id = futures[future]
                try:
                    result = future.result()
                    results[tool_id] = result
                except Exception as e:
                    logger.error(f"Tool execution failed for {tool_id}: {str(e)}")
                    results[tool_id] = {"error": str(e)}
        
        return results
    
    def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        tool_invoke_fn,
    ) -> Dict[str, Any]:
        """Execute a single tool call."""
        tool_id = tool_call.get("id")
        tool_name = tool_call.get("tool") or tool_call.get("name")
        tool_input = tool_call.get("tool_input") or tool_call.get("input", {})
        
        try:
            result = tool_invoke_fn(tool_name, tool_input)
            return {tool_id: result}
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_id}: {str(e)}")
            return {tool_id: {"error": str(e)}}
    
    def shutdown(self):
        """Shutdown the executor."""
        if self.executor:
            self.executor.shutdown(wait=True)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


def create_parallel_executor(max_workers: int = 4, use_asyncio: bool = True) -> ParallelToolExecutor:
    """Create a parallel tool executor.
    
    Args:
        max_workers: Maximum number of concurrent workers
        use_asyncio: Use asyncio or ThreadPoolExecutor
        
    Returns:
        Configured ParallelToolExecutor instance
    """
    return ParallelToolExecutor(max_workers=max_workers, use_asyncio=use_asyncio)
