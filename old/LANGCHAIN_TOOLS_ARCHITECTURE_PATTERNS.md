# LangChain Tools - Architecture and Best Practices

## Tool Architecture Overview

### Tool System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    LangChain Tool System                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tool Definition Layer                                       │
│  ├── @tool decorator                                         │
│  ├── BaseTool class                                          │
│  ├── Pydantic BaseModel                                      │
│  └── Callable/Function                                       │
│                                                              │
│  Tool Schema Layer                                           │
│  ├── Type inference from annotations                         │
│  ├── Pydantic schema generation                              │
│  ├── JSON schema output                                      │
│  └── Tool call schema (LLM format)                          │
│                                                              │
│  Binding Layer                                               │
│  ├── bind_tools() on LLM                                     │
│  ├── Provider-specific formatting                           │
│  ├── tool_choice parameter handling                          │
│  └── Runnable integration                                    │
│                                                              │
│  Execution Layer                                             │
│  ├── Tool invocation                                         │
│  ├── Argument validation                                     │
│  ├── Error handling                                          │
│  └── Callback management                                     │
│                                                              │
│  Integration Layer                                           │
│  ├── AgentExecutor (legacy)                                  │
│  ├── LangGraph agents (modern)                               │
│  ├── Tool message handling                                   │
│  └── Agentic loops                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Tool Definition Patterns

### Pattern 1: Decorator-Based Tools (Recommended for Simple Tools)

**Pros:**
- Simple and concise
- Automatic schema inference
- Less boilerplate

**Cons:**
- Limited customization
- Not suitable for complex initialization

**Example:**
```python
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    return "results"
```

**When to use:**
- Simple utility functions
- Stateless operations
- Quick prototyping

### Pattern 2: Class-Based Tools (Recommended for Complex Tools)

**Pros:**
- Maximum control
- Can maintain state
- Custom initialization
- Flexible validation

**Cons:**
- More boilerplate
- Requires implementing `_run` and `_arun`

**Example:**
```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel

class MyToolInput(BaseModel):
    param: str

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "Tool description"
    args_schema: type[BaseModel] = MyToolInput
    
    def _run(self, param: str) -> str:
        return f"result"
    
    async def _arun(self, param: str) -> str:
        return f"result"
```

**When to use:**
- Complex tools with state
- Tools requiring special initialization
- Tools with custom validation logic

### Pattern 3: Pydantic Model Tools (Recommended for Schema-First Approach)

**Pros:**
- Type-safe
- Built-in validation
- Works well with structured output

**Cons:**
- Less execution flexibility
- Requires separate execution logic

**Example:**
```python
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get weather information."""
    location: str = Field(..., description="City and state")
    units: str = Field(default="fahrenheit", description="Temperature units")

# Use directly with bind_tools
model = llm.bind_tools([GetWeather])
```

**When to use:**
- Structured APIs
- Type-safe tool definitions
- Integration with structured output APIs

## Schema Design Patterns

### Pattern 1: Flat Arguments

**Best for:** Simple tools with few arguments

```python
@tool
def search(query: str, limit: int = 10) -> str:
    """Search with simple args."""
    return "results"

# Generated schema:
# {
#     "properties": {
#         "query": {"type": "string"},
#         "limit": {"type": "integer", "default": 10}
#     },
#     "required": ["query"]
# }
```

### Pattern 2: Nested Structures

**Best for:** Tools with many related parameters

```python
from pydantic import BaseModel, Field

class FilterOptions(BaseModel):
    min_price: float = Field(..., description="Minimum price")
    max_price: float = Field(..., description="Maximum price")
    category: str = Field(..., description="Product category")

class SearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    filters: FilterOptions = Field(default_factory=FilterOptions, description="Filter options")

@tool(args_schema=SearchInput)
def advanced_search(query: str, filters: FilterOptions) -> str:
    """Advanced product search."""
    return "results"
```

### Pattern 3: Enum for Fixed Choices

**Best for:** Tools with specific valid options

```python
from enum import Enum
from pydantic import BaseModel, Field

class SortBy(str, Enum):
    """Sort options."""
    RELEVANCE = "relevance"
    PRICE_LOW = "price_low"
    PRICE_HIGH = "price_high"
    RATING = "rating"

class SearchInput(BaseModel):
    query: str
    sort_by: SortBy = Field(default=SortBy.RELEVANCE, description="Sort results by")

@tool(args_schema=SearchInput)
def smart_search(query: str, sort_by: SortBy) -> str:
    """Search with sorting options."""
    return "results"
```

## Tool Execution Patterns

### Pattern 1: Direct Execution

**Use when:** Tool runs synchronously and returns immediately

```python
@tool
def add(a: int, b: int) -> str:
    """Add numbers."""
    return str(a + b)

# Direct use
result = add.invoke({"a": 5, "b": 3})
```

### Pattern 2: Async Execution

**Use when:** Tool involves I/O operations (network, database)

```python
@tool
async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

# Async use
result = await fetch_data.ainvoke({"url": "https://example.com"})
```

### Pattern 3: Streaming Execution

**Use when:** Tool produces incremental results

```python
from langchain_core.callbacks import CallbackManagerForToolRun

@tool
def process_large_data(
    data: list,
    run_manager: CallbackManagerForToolRun = None
) -> str:
    """Process data with streaming."""
    results = []
    for item in data:
        result = process_item(item)
        results.append(result)
        
        if run_manager:
            run_manager.on_text(f"Processed: {item}")
    
    return ",".join(results)
```

## Tool Integration Patterns

### Pattern 1: Single Tool Agent

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for {query}"

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
agent = create_react_agent(llm, [search])

result = agent.invoke({"messages": [("user", "Search for Python")]})
```

### Pattern 2: Multi-Tool Agent with Orchestration

```python
from langchain_core.tools import tool
from typing import Union

@tool
def search(query: str) -> str:
    """Search external sources."""
    return f"Search results: {query}"

@tool
def calculate(expression: str) -> str:
    """Calculate expressions."""
    return str(eval(expression))

@tool
def summarize(text: str) -> str:
    """Summarize text."""
    return f"Summary: {text[:100]}..."

# Create agent with tool orchestration
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
tools = [search, calculate, summarize]

model = llm.bind_tools(tools)

# Agent handles routing and execution
response = model.invoke("Search for AI news and summarize")
```

### Pattern 3: Tool Dependency Graph

```python
from typing import Dict, List, Callable

class ToolDependencyGraph:
    """Manage tool dependencies."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.dependencies: Dict[str, List[str]] = {}
    
    def add_tool(self, name: str, tool: Callable, deps: List[str] = None):
        """Add tool with dependencies."""
        self.tools[name] = tool
        self.dependencies[name] = deps or []
    
    def execute(self, tool_name: str, args: dict):
        """Execute tool respecting dependencies."""
        deps = self.dependencies.get(tool_name, [])
        
        # Execute dependencies first
        for dep in deps:
            # Recursively execute
            self.execute(dep, args)
        
        # Execute target tool
        return self.tools[tool_name](**args)

# Usage
graph = ToolDependencyGraph()
graph.add_tool("search", search_tool)
graph.add_tool("extract", extract_tool, deps=["search"])
graph.add_tool("analyze", analyze_tool, deps=["extract"])

result = graph.execute("analyze", {"query": "python"})
```

## Error Handling Patterns

### Pattern 1: Tool Exception Raising

```python
from langchain_core.tools import tool, ToolException

@tool
def validate_and_process(data: str) -> str:
    """Validate and process data."""
    try:
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Process
        result = process(data)
        return result
    except ValueError as e:
        # Raise ToolException for agent to handle
        raise ToolException(f"Validation failed: {str(e)}")
    except Exception as e:
        # Log and re-raise
        logger.error(f"Unexpected error: {e}")
        raise ToolException(f"Processing failed: {str(e)}")
```

### Pattern 2: Fallback Tools

```python
@tool
def primary_search(query: str) -> str:
    """Primary search source."""
    try:
        return search_api_1(query)
    except Exception:
        # Falls back to secondary via agent
        raise ToolException("Primary search failed, try fallback")

@tool
def fallback_search(query: str) -> str:
    """Fallback search source."""
    return search_api_2(query)

# Agent can be instructed to try fallback_search on failure
tools = [primary_search, fallback_search]
```

### Pattern 3: Retry Logic

```python
from functools import wraps
import time

def retry_tool(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for tool retry logic."""
    def decorator(tool_func):
        @wraps(tool_func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return tool_func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise ToolException(f"Failed after {max_attempts} attempts: {last_error}")
        return wrapper
    return decorator

@tool
@retry_tool(max_attempts=3, delay=1.0)
def flaky_api(query: str) -> str:
    """API that might fail."""
    return api_call(query)
```

## Validation Patterns

### Pattern 1: Pydantic Validators

```python
from pydantic import BaseModel, field_validator

class EmailInput(BaseModel):
    email: str
    name: str
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError("Name too short")
        return v.strip()

@tool(args_schema=EmailInput)
def send_email(email: str, name: str) -> str:
    """Send email with validation."""
    return f"Email sent to {name}"
```

### Pattern 2: Custom Validation

```python
from langchain_core.tools import tool, ToolException

@tool
def process_numbers(numbers: list[float]) -> str:
    """Process list of numbers."""
    # Validate
    if not numbers:
        raise ToolException("Numbers list cannot be empty")
    
    if len(numbers) > 1000:
        raise ToolException("Too many numbers (max 1000)")
    
    if any(n < 0 for n in numbers):
        raise ToolException("Negative numbers not allowed")
    
    # Process
    result = sum(numbers) / len(numbers)
    return f"Average: {result}"
```

## Performance Patterns

### Pattern 1: Caching

```python
from functools import lru_cache
from langchain_core.tools import tool

@tool
def expensive_operation(param: str) -> str:
    """Expensive operation with caching."""
    return cached_compute(param)

@lru_cache(maxsize=128)
def cached_compute(param: str) -> str:
    """Cached computation."""
    return compute(param)
```

### Pattern 2: Rate Limiting

```python
import time
from functools import wraps

def rate_limit(calls_per_second: float = 1.0):
    """Rate limiting decorator."""
    min_interval = 1.0 / calls_per_second
    last_call = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

@tool
@rate_limit(calls_per_second=10)
def api_call(query: str) -> str:
    """Rate-limited API call."""
    return api.search(query)
```

### Pattern 3: Batching

```python
from typing import List
from langchain_core.tools import tool

@tool
def batch_process(items: List[str], batch_size: int = 10) -> str:
    """Process items in batches."""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = process_batch(batch)
        results.extend(batch_results)
    
    return f"Processed {len(results)} items"
```

## Testing Patterns

### Pattern 1: Unit Testing Tools

```python
import pytest
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Add numbers."""
    return a + b

def test_add_positive():
    assert add.invoke({"a": 2, "b": 3}) == 5

def test_add_negative():
    assert add.invoke({"a": -1, "b": 1}) == 0

def test_add_schema():
    assert add.name == "add"
    assert "a" in add.args
    assert "b" in add.args
```

### Pattern 2: Integration Testing with Mock LLM

```python
from unittest.mock import Mock
from langchain_core.messages import AIMessage

def test_tool_with_mock_llm():
    """Test tool usage with mock LLM."""
    mock_llm = Mock()
    mock_llm.invoke.return_value = AIMessage(
        content="",
        tool_calls=[{
            "name": "add",
            "args": {"a": 5, "b": 3},
            "id": "call_123",
            "type": "tool_call"
        }]
    )
    
    model = mock_llm.bind_tools([add])
    response = model.invoke("What is 5 + 3?")
    
    assert response.tool_calls[0]["name"] == "add"
    assert response.tool_calls[0]["args"] == {"a": 5, "b": 3}
```

### Pattern 3: End-to-End Agent Testing

```python
def test_agent_with_tools():
    """Test complete agent workflow."""
    from langgraph.prebuilt import create_react_agent
    
    llm = ChatAnthropic(model="claude-3-sonnet-20240229")
    agent = create_react_agent(llm, [search_tool, calculate_tool])
    
    result = agent.invoke({
        "messages": [("user", "Search for X and calculate Y")]
    })
    
    # Verify agent completed
    final_msg = result["messages"][-1]
    assert final_msg.type == "ai"
    assert final_msg.content  # Has final answer
```

## Monitoring and Observability Patterns

### Pattern 1: Tool Execution Logging

```python
import logging
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)

@tool
def logged_operation(data: str, run_manager: CallbackManagerForToolRun = None) -> str:
    """Operation with logging."""
    logger.info(f"Starting operation with data: {data}")
    
    if run_manager:
        run_manager.on_text(f"Processing: {data}")
    
    try:
        result = process(data)
        logger.info(f"Operation successful: {result}")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

### Pattern 2: Tool Metrics

```python
from time import time
from typing import Callable, Any

class ToolMetrics:
    """Track tool execution metrics."""
    
    def __init__(self):
        self.calls = {}
        self.errors = {}
        self.timings = {}
    
    def track(self, tool_func: Callable) -> Callable:
        """Decorator to track metrics."""
        def wrapper(*args, **kwargs):
            start = time()
            tool_name = tool_func.__name__
            
            try:
                result = tool_func(*args, **kwargs)
                self.calls[tool_name] = self.calls.get(tool_name, 0) + 1
                return result
            except Exception as e:
                self.errors[tool_name] = self.errors.get(tool_name, 0) + 1
                raise
            finally:
                elapsed = time() - start
                if tool_name not in self.timings:
                    self.timings[tool_name] = []
                self.timings[tool_name].append(elapsed)
        
        return wrapper

metrics = ToolMetrics()

@tool
@metrics.track
def tracked_tool(query: str) -> str:
    """Tool with metrics tracking."""
    return "result"
```

These patterns provide a comprehensive foundation for building robust,
scalable tool systems with LangChain.
