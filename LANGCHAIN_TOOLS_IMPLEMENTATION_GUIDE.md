# LangChain Tool Implementation Guide

## Overview
This guide provides comprehensive information about how LangChain implements tool usage with LLMs, including proper tool definition, binding, and processing of tool calls from LLM responses.

---

## 1. Tool Definition Patterns

### 1.1 The `@tool` Decorator

The simplest way to create a tool using the `@tool` decorator:

```python
from langchain_core.tools import tool
from typing import Annotated

@tool
def search_api(query: str) -> str:
    """Search the API for the query."""
    return "API result"

# Tool is now a BaseTool instance
print(search_api.name)  # "search_api"
print(search_api.description)  # "Search the API for the query."
```

**Key Features:**
- Automatically infers tool name from function name
- Uses docstring as description
- Generates JSON schema from function signature
- Supports both sync and async functions

### 1.2 Tool with Custom Schema using `@tool`

Define custom argument schema with Pydantic models:

```python
from pydantic import BaseModel, Field
from langchain_core.tools import tool

class SearchInput(BaseModel):
    """Input for search tool."""
    query: str = Field(..., description="The search query")
    max_results: int = Field(default=10, description="Max results to return")

@tool(args_schema=SearchInput)
def search(query: str, max_results: int = 10) -> str:
    """Search for information."""
    return f"Searching for {query} with {max_results} results"
```

### 1.3 Tool Decorator with Parameters

```python
from langchain_core.tools import tool

@tool(
    name="custom_search",
    description="Search with a custom description",
    return_direct=True,  # Return result directly without agent processing
    parse_docstring=True  # Parse docstring for detailed descriptions
)
def my_tool(x: int) -> str:
    """Detailed description in docstring.
    
    Args:
        x: The input parameter with detailed description
    """
    return str(x)
```

**Decorator Parameters:**
- `name`: Custom tool name (defaults to function name)
- `description`: Override docstring description
- `return_direct`: Skip agent loop and return directly
- `args_schema`: Pydantic BaseModel for argument validation
- `parse_docstring`: Parse Google-style docstrings for detailed arg descriptions
- `error_on_invalid_docstring`: Raise error if docstring is invalid

### 1.4 BaseTool Class Subclass

For more control, subclass `BaseTool`:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional

class CalculatorInput(BaseModel):
    """Input for calculator."""
    a: int = Field(..., description="First number")
    b: int = Field(..., description="Second number")

class Calculator(BaseTool):
    name: str = "calculator"
    description: str = "Perform arithmetic operations"
    args_schema: type[BaseModel] = CalculatorInput
    
    def _run(self, a: int, b: int) -> str:
        """Execute the tool."""
        return str(a + b)
    
    async def _arun(self, a: int, b: int) -> str:
        """Async execution."""
        return str(a + b)
```

**Important Properties:**
- `name`: Unique identifier for the tool
- `description`: Used by LLM to decide when to use tool
- `args_schema`: Type annotation must be `type[BaseModel]` (NOT just `BaseModel`)

### 1.5 Tool Schema Validation

The `args_schema` annotation must be properly typed:

```python
# CORRECT - Type annotation as type[BaseModel]
class MyTool(BaseTool):
    args_schema: type[BaseModel] = MySchema  # Correct

# INCORRECT - This will raise SchemaAnnotationError
class MyTool(BaseTool):
    args_schema: BaseModel = MySchema  # Wrong!
```

### 1.6 Tool Definition from Runnable

Convert any Runnable to a tool:

```python
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

class Args(BaseModel):
    a: int
    b: list[int]

def multiply_sum(x: dict) -> str:
    return str(x["a"] * sum(x["b"]))

runnable = RunnableLambda(multiply_sum)
tool = runnable.as_tool(args_schema=Args, name="multiply_sum")
```

### 1.7 Pydantic Model as Tool Definition

Directly use Pydantic BaseModel as tool:

```python
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get the current weather in a location."""
    location: str = Field(..., description="City and state, e.g., San Francisco, CA")
    
# Use with bind_tools
model_with_tools = llm.bind_tools([GetWeather, GetPrice])
```

### 1.8 Tool with Annotated Arguments

Use `Annotated` for detailed argument descriptions:

```python
from typing import Annotated
from langchain_core.tools import tool

@tool
def search(
    query: Annotated[str, "The search query string"],
    limit: Annotated[int, "Maximum number of results"],
) -> str:
    """Search for information."""
    return f"Found {limit} results for {query}"
```

### 1.9 Tool with Injected Arguments

Use `InjectedToolArg` to inject values not provided by LLM:

```python
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg
from langchain_core.messages import ToolMessage

@tool
def my_tool(
    x: int,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> ToolMessage:
    """Tool that receives the tool call ID."""
    return ToolMessage(
        content=str(x),
        tool_call_id=tool_call_id,
        name="my_tool"
    )
```

### 1.10 Tool from Function with Manual Schema

```python
from langchain_core.tools import Tool

def search_api(query: str) -> str:
    """Search implementation."""
    return f"Results for {query}"

# Create Tool with explicit parameters
tool = Tool.from_function(
    func=search_api,
    name="search",
    description="Search the API",
    return_direct=False,
    coroutine=None  # async version
)
```

---

## 2. Tool Binding to LLMs

### 2.1 Basic Tool Binding

Bind tools to chat models using `bind_tools()`:

```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get the current weather."""
    location: str = Field(..., description="City and state, e.g., San Francisco, CA")

class GetPrice(BaseModel):
    """Get the price of a product."""
    product: str = Field(..., description="The product to look up")

llm = ChatAnthropic(model="claude-3-sonnet-20240229")

# Bind tools to model
model_with_tools = llm.bind_tools([GetWeather, GetPrice])

# Invoke
response = model_with_tools.invoke("What's the weather in San Francisco?")
```

### 2.2 Tool Choice Parameter

Control which tool the model must call:

```python
# Auto: Model decides if tool is needed
model_auto = llm.bind_tools([GetWeather, GetPrice], tool_choice="auto")

# Any: Force at least one tool to be called
model_any = llm.bind_tools([GetWeather, GetPrice], tool_choice="any")

# Specific tool by name
model_specific = llm.bind_tools([GetWeather, GetPrice], tool_choice="GetWeather")

# Force none: Don't call any tool
model_none = llm.bind_tools([GetWeather, GetPrice], tool_choice="none")
```

**OpenAI format:**
```python
# Specific tool with dict
model = llm.bind_tools(
    [GetWeather, GetPrice],
    tool_choice={"type": "function", "function": {"name": "GetWeather"}}
)
```

**Anthropic format:**
```python
# Specific tool with Anthropic dict
model = llm.bind_tools(
    [GetWeather, GetPrice],
    tool_choice={"type": "tool", "name": "GetWeather"}
)
```

### 2.3 Supported Tool Formats

`bind_tools()` accepts multiple tool definition formats:

```python
# 1. Pydantic BaseModel
from pydantic import BaseModel

class Tool1(BaseModel):
    """Tool description."""
    param: str

# 2. Callable/Function
def tool_func(param: str) -> str:
    """Tool description."""
    return param

# 3. BaseTool instances
from langchain_core.tools import Tool

tool_obj = Tool(
    name="tool_name",
    func=lambda x: x,
    description="Description"
)

# 4. Dict schema (provider-specific)
tool_dict = {
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "Description",
        "parameters": {...}
    }
}

# Bind any combination
model_with_tools = llm.bind_tools([Tool1, tool_func, tool_obj, tool_dict])
```

### 2.4 Tool Format Conversion

LangChain automatically converts tools to provider format:

```python
from langchain_core.utils.function_calling import convert_to_openai_tool

# Convert to OpenAI format
openai_tool = convert_to_openai_tool(GetWeather)
# Result:
# {
#     "type": "function",
#     "function": {
#         "name": "GetWeather",
#         "description": "Get the current weather...",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "location": {
#                     "type": "string",
#                     "description": "City and state..."
#                 }
#             },
#             "required": ["location"]
#         }
#     }
# }
```

### 2.5 Multiple Tools Binding

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@tool
def subtract(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

# Bind all tools
model = llm.bind_tools([add, subtract, multiply])
```

---

## 3. Processing Tool Calls from LLM Responses

### 3.1 Accessing Tool Calls from AIMessage

Tool calls are available in the `AIMessage.tool_calls` field:

```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get the current weather."""
    location: str

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([GetWeather])

response = model_with_tools.invoke("What's the weather in San Francisco?")

# Access tool calls
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call['name']}")
        print(f"Args: {tool_call['args']}")
        print(f"ID: {tool_call['id']}")
```

### 3.2 ToolCall TypedDict Structure

The `ToolCall` type has this structure:

```python
from langchain_core.messages.tool import ToolCall

# ToolCall is a TypedDict with:
{
    "name": str,           # Tool function name
    "args": dict,          # Arguments as dictionary
    "id": str | None,      # Unique identifier for this call
    "type": "tool_call"    # Fixed literal
}
```

Example:
```python
tool_call = {
    "name": "GetWeather",
    "args": {"location": "San Francisco, CA"},
    "id": "call_123abc",
    "type": "tool_call"
}
```

### 3.3 Processing Individual Tool Calls

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage

class Calculator(BaseModel):
    """Simple calculator."""
    operation: str
    a: int
    b: int

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([Calculator])

response = model_with_tools.invoke("Calculate 5 + 3")

# Process tool calls
for tool_call in response.tool_calls:
    if tool_call["name"] == "Calculator":
        args = tool_call["args"]
        operation = args.get("operation")
        a = args.get("a")
        b = args.get("b")
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        # ... etc
        
        # Create tool response message
        tool_response = ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"],
            name=tool_call["name"]
        )
```

### 3.4 Creating ToolMessage for Responses

Pass tool results back to model using `ToolMessage`:

```python
from langchain_core.messages import ToolMessage

# Execute tool
tool_output = execute_tool(
    tool_name=tool_call["name"],
    args=tool_call["args"]
)

# Create response message
tool_msg = ToolMessage(
    content=tool_output,                    # String result of tool execution
    tool_call_id=tool_call["id"],          # Must match original tool_call["id"]
    name=tool_call["name"],                # Tool name (optional but recommended)
    artifact=tool_output  # Complex output not sent to model (optional)
)

# Continue conversation
messages = [
    HumanMessage(content="original query"),
    response,  # AIMessage with tool_calls
    tool_msg   # ToolMessage with result
]

next_response = model.invoke(messages)
```

### 3.5 Parsing Tool Calls (Legacy Method)

For backward compatibility with `additional_kwargs`:

```python
import json
from langchain_core.messages import AIMessage

def parse_tool_calls(message: AIMessage):
    """Parse tool calls from message."""
    # Preferred: use message.tool_calls
    if message.tool_calls:
        return message.tool_calls
    
    # Legacy: parse from additional_kwargs
    tool_calls = message.additional_kwargs.get("tool_calls", [])
    parsed = []
    
    for tc in tool_calls:
        function = tc["function"]
        args = json.loads(function["arguments"])
        parsed.append({
            "name": function["name"],
            "args": args,
            "id": tc["id"],
            "type": "tool_call"
        })
    
    return parsed
```

### 3.6 Handling Invalid Tool Calls

```python
from langchain_core.messages import InvalidToolCall

# Check for invalid tool calls
if response.invalid_tool_calls:
    for invalid_call in response.invalid_tool_calls:
        print(f"Invalid tool: {invalid_call['name']}")
        print(f"Error: {invalid_call.get('error')}")
        print(f"Args: {invalid_call['args']}")  # Raw unparsed args
```

### 3.7 Tool Call Parsing Functions

LangChain provides utilities for parsing tool calls:

```python
from langchain_core.output_parsers.openai_tools import parse_tool_call, parse_tool_calls

# Parse single tool call
raw_tool_call = {
    "id": "call_123",
    "function": {
        "name": "GetWeather",
        "arguments": '{"location": "SF"}'
    }
}

parsed = parse_tool_call(raw_tool_call)
# Returns: {"name": "GetWeather", "args": {"location": "SF"}, "id": "call_123"}

# Parse multiple
raw_calls = [raw_tool_call, ...]
parsed_calls = parse_tool_calls(raw_calls)
```

### 3.8 Complete Agent Loop Example

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, ToolMessage
)
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get weather."""
    location: str = Field(..., description="City and state")

def get_weather(location: str) -> str:
    """Simulate weather tool."""
    return f"Weather in {location}: Sunny, 75°F"

# Setup
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([GetWeather])

# Agent loop
messages: list[BaseMessage] = [
    HumanMessage(content="What's the weather in San Francisco?")
]

while True:
    # Get response from model
    response = model_with_tools.invoke(messages)
    messages.append(response)
    
    # Check if model wants to use tools
    if not response.tool_calls:
        # Final response
        print(f"Final: {response.content}")
        break
    
    # Process each tool call
    for tool_call in response.tool_calls:
        if tool_call["name"] == "GetWeather":
            tool_output = get_weather(**tool_call["args"])
            
            # Add tool result to messages
            messages.append(ToolMessage(
                content=tool_output,
                tool_call_id=tool_call["id"],
                name="GetWeather"
            ))
```

---

## 4. AgentExecutor Pattern

### 4.1 Classic AgentExecutor (Deprecated)

The old pattern using `AgentExecutor`:

```python
from langchain_classic.agents import AgentExecutor, initialize_agent, AgentType
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import Tool

llm = ChatAnthropic(model="claude-3-sonnet-20240229")

tools = [
    Tool(
        name="Search",
        func=lambda x: "Result",
        description="Search the internet"
    )
]

# Initialize agent (deprecated)
agent_executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

result = agent_executor.run("What is the capital of France?")
```

**Status:** This pattern is deprecated. Use LangGraph instead.

### 4.2 Modern Pattern with LangGraph

LangGraph is the recommended approach:

```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for {query}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
tools = [search, calculator]

# Create agent
agent = create_react_agent(llm, tools)

# Run
result = agent.invoke({
    "messages": [("user", "What's 2+2?")]
})

print(result["messages"][-1].content)
```

### 4.3 Tool Execution in Agents

When AgentExecutor calls tools:

```python
# 1. Model outputs action
action = AgentAction(tool="tool_name", tool_input={"param": "value"})

# 2. Tool is looked up and executed
tool = name_to_tool_map[action.tool]
observation = tool.run(action.tool_input)

# 3. Observation is added to state
agent_step = AgentStep(action=action, observation=observation)

# 4. Continue until tool returns finish
if tool.return_direct:
    return AgentFinish(
        return_values={"output": observation},
        log="..."
    )
```

### 4.4 Tool Return Direct Flag

The `return_direct` property controls agent loop behavior:

```python
@tool(return_direct=True)
def final_answer(answer: str) -> str:
    """Return final answer - stops agent loop."""
    return answer

# With return_direct=True:
# - Tool executes
# - Agent loop stops
# - Result returned directly

# With return_direct=False (default):
# - Tool executes
# - Agent continues (may call more tools)
# - Agent decides when to finish
```

---

## 5. Best Practices for Tool Definitions

### 5.1 Clear Descriptions

Descriptions are crucial for LLM decision-making:

```python
# BAD - Too vague
@tool
def search(query: str) -> str:
    """Search."""
    return "result"

# GOOD - Clear purpose and usage
@tool
def search_product_database(query: str) -> str:
    """Search the product database for items matching the query.
    
    Use this when the user wants to find products by name, category, or features.
    """
    return "result"
```

### 5.2 Detailed Parameter Descriptions

```python
from pydantic import BaseModel, Field
from langchain_core.tools import tool

class SearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The search query - can include product names, "
                   "categories like 'electronics' or 'clothing'"
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return (1-100)"
    )
    sort_by: str = Field(
        default="relevance",
        description="Sort results by: 'relevance', 'price_low', 'price_high', 'rating'"
    )

@tool(args_schema=SearchInput)
def search(query: str, max_results: int = 10, sort_by: str = "relevance") -> str:
    """Search product database."""
    return "results"
```

### 5.3 Type Hints Matter

```python
# Type hints are converted to JSON schema
@tool
def process_data(
    values: list[int],           # Array in schema
    options: dict[str, str],      # Object in schema
    threshold: float = 0.5,       # Number in schema
    active: bool = True           # Boolean in schema
) -> str:
    """Process data."""
    return "done"
```

### 5.4 Handling Tool Failures

```python
from langchain_core.tools import tool, ToolException

@tool
def risky_operation(param: str) -> str:
    """Perform risky operation."""
    try:
        # Do something risky
        if not valid(param):
            raise ValueError(f"Invalid parameter: {param}")
        return result
    except Exception as e:
        # Raise ToolException for agent to handle
        raise ToolException(f"Operation failed: {str(e)}")
```

### 5.5 Validation in args_schema

Use Pydantic validators:

```python
from pydantic import BaseModel, Field, field_validator

class EmailInput(BaseModel):
    email: str = Field(..., description="Email address")
    
    @field_validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v.lower()

@tool(args_schema=EmailInput)
def send_email(email: str) -> str:
    """Send email."""
    return f"Email sent to {email}"
```

### 5.6 Few-shot Examples in Description

```python
@tool
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Calculate distance between two geographic points.
    
    This uses the Haversine formula to calculate the great-circle distance
    in kilometers.
    
    Examples:
    - Distance from San Francisco (37.7749, -122.4194) to 
      Los Angeles (34.0522, -118.2437) is ~559 km
    - Distance from New York (40.7128, -74.0060) to 
      Boston (42.3601, -71.0589) is ~309 km
    """
    # implementation
    pass
```

### 5.7 Tool Organization with Toolkits

```python
from langchain_core.tools import BaseToolkit, BaseTool

class CalculatorToolkit(BaseToolkit):
    """Tools for mathematical operations."""
    
    def get_tools(self) -> list[BaseTool]:
        return [
            add_tool,
            subtract_tool,
            multiply_tool,
            divide_tool
        ]

# Use toolkit
toolkit = CalculatorToolkit()
agent = create_react_agent(llm, toolkit.get_tools())
```

### 5.8 Async Tool Implementation

```python
from langchain_core.tools import tool

@tool
async def fetch_data(url: str) -> str:
    """Fetch data from URL asynchronously."""
    # This will be called with await if agent supports it
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()
```

### 5.9 Tool with Multiple Return Types

```python
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

@tool
def analyze_data(data: list[float]) -> ToolMessage:
    """Analyze numerical data."""
    # Return ToolMessage with both content and artifact
    # Artifact for data not sent to LLM, content for LLM
    return ToolMessage(
        content=f"Mean: {sum(data)/len(data):.2f}",
        artifact={"mean": sum(data)/len(data), "data": data},
        tool_call_id="call_id",
        name="analyze_data"
    )
```

### 5.10 Tool Metadata and Caching

```python
@tool
def expensive_operation(param: str) -> str:
    """Perform expensive operation that could be cached."""
    return f"Result for {param}"

# Add metadata
expensive_operation.metadata = {
    "category": "data_processing",
    "cost": "high",
    "cacheable": True
}

# Tools can be tagged
expensive_operation.tags = ["slow", "expensive"]
```

---

## 6. Tool Schema and JSON Schema Generation

### 6.1 Schema Formats

LangChain generates schemas in multiple formats:

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(..., description="Search term")
    limit: int = Field(default=10, description="Result limit")

@tool(args_schema=SearchInput)
def search(query: str, limit: int = 10) -> str:
    return "results"

# Access different schema formats
print(search.args_schema)  # Pydantic model class
print(search.args)        # Dict of properties
print(search.tool_call_schema)  # Schema for tool calls only
```

### 6.2 OpenAI Tool Format

```python
# Generated by bind_tools for OpenAI:
{
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search for information...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Result limit"
                }
            },
            "required": ["query"]
        }
    }
}
```

### 6.3 Anthropic Tool Format

```python
# Generated by bind_tools for Anthropic:
{
    "name": "search",
    "description": "Search for information...",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term"
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Result limit"
            }
        },
        "required": ["query"]
    }
}
```

---

## 7. Advanced Patterns

### 7.1 Dynamic Tool Binding

```python
def create_tools_dynamically(tool_names: list[str]) -> list[BaseTool]:
    """Create tools based on a list of names."""
    tools = []
    
    for name in tool_names:
        @tool(name=name)
        def dynamic_tool(query: str) -> str:
            return f"Result from {name}"
        
        tools.append(dynamic_tool)
    
    return tools

# Use
tool_names = ["search", "calculate", "translate"]
tools = create_tools_dynamically(tool_names)
model = llm.bind_tools(tools)
```

### 7.2 Tool with Context/Configuration

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
def context_aware_tool(
    query: str,
    run_manager: "CallbackManagerForToolRun | None" = None
) -> str:
    """Tool that uses context/callbacks."""
    if run_manager:
        run_manager.on_text(f"Processing: {query}")
    return f"Result for {query}"
```

### 7.3 Tool Composition

```python
from langchain_core.runnables import Runnable

# Compose tools into pipelines
extract_tool = create_extraction_tool()
analyze_tool = create_analysis_tool()
summarize_tool = create_summary_tool()

# Chain tools
pipeline = extract_tool | analyze_tool | summarize_tool

# Convert to single tool
composed_tool = pipeline.as_tool(
    name="data_pipeline",
    description="Extract, analyze, and summarize data"
)
```

---

## 8. Common Issues and Solutions

### 8.1 Tool Not Being Called

**Problem:** LLM doesn't call the tool even when appropriate.

**Solutions:**
- Make description clearer and more specific
- Add usage examples to description
- Use `tool_choice="any"` or `tool_choice="tool_name"` to force tool use
- Ensure tool schema is valid

```python
@tool(tool_choice="any")  # Force tool usage
def my_tool(query: str) -> str:
    """Clear description with specific use case.
    
    Use this tool when the user asks about [specific domain].
    
    Examples:
    - "What is X?" -> use this tool
    """
    return result
```

### 8.2 Incorrect Tool Arguments

**Problem:** Tool receives wrong argument types or missing required args.

**Solutions:**
- Use strict Pydantic schema with validators
- Provide clear type hints
- Use `strict=True` in model binding (when supported)

```python
from pydantic import BaseModel, validator

class ToolInput(BaseModel):
    value: int
    
    @validator("value")
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Value must be positive")
        return v
```

### 8.3 Tool Not Found / Invalid Tool Call

**Problem:** "Tool not found" or invalid tool call errors.

**Solutions:**
- Ensure tool name matches exactly (case-sensitive)
- Check that all required arguments are provided
- Look for typos in tool names

```python
# Tool name must match exactly
@tool(name="get_weather")
def weather_tool(location: str) -> str:
    return "..."

# If LLM uses "GetWeather", it will fail
# Provide clear name in decorator
```

### 8.4 Tool Arguments Not Parsing

**Problem:** JSON parsing fails for tool arguments.

**Solutions:**
- Ensure args are valid JSON format
- Use `partial=True` for streaming tool calls
- Check for string escaping issues

```python
# In agent loop, handle parse failures:
try:
    args = json.loads(tool_call["function"]["arguments"])
except json.JSONDecodeError as e:
    # Handle parsing error
    error_msg = f"Failed to parse arguments: {str(e)}"
    # Continue with error message to LLM
```

### 8.5 Tool Return Value Issues

**Problem:** Tool return value not properly formatted.

**Solutions:**
- Always return strings (LLM expects strings)
- For complex data, serialize to JSON string
- Use `ToolMessage` with artifact for complex outputs

```python
import json

@tool
def process_data(data: list[int]) -> str:
    """Process data."""
    result = {
        "sum": sum(data),
        "mean": sum(data) / len(data),
        "count": len(data)
    }
    # Return as JSON string
    return json.dumps(result)
```

---

## 9. Testing Tools

### 9.1 Basic Tool Testing

```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

# Test directly
assert add.invoke({"a": 2, "b": 3}) == 5
assert add.invoke({"a": -1, "b": 1}) == 0

# Test schema
assert add.name == "add"
assert "Add two numbers" in add.description
```

### 9.2 Testing with Mock LLM

```python
from langchain_core.language_models.llm import LLM
from unittest.mock import Mock
from langchain_core.messages import AIMessage

# Create mock LLM that returns specific tool calls
mock_llm = Mock(spec=LLM)
mock_llm.invoke.return_value = AIMessage(
    content="",
    tool_calls=[{
        "name": "add",
        "args": {"a": 5, "b": 3},
        "id": "call_123",
        "type": "tool_call"
    }]
)

# Use in agent
model_with_tools = mock_llm.bind_tools([add])
response = model_with_tools.invoke("What is 5+3?")
assert response.tool_calls[0]["name"] == "add"
```

### 9.3 Integration Testing

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

@tool
def test_tool(query: str) -> str:
    """Test tool for integration tests."""
    return f"Processed: {query}"

# Test with real LLM (requires API key)
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([test_tool])

response = model_with_tools.invoke("Use test_tool with 'hello'")
assert response.tool_calls
assert response.tool_calls[0]["name"] == "test_tool"
```

---

## 10. Provider-Specific Notes

### 10.1 OpenAI

- Uses `function` tool type
- Supports `tool_choice`: "auto", "none", "required", tool name, or dict
- Arguments must be valid JSON
- No parallel tool calls by default

### 10.2 Anthropic

- Uses `tool_use` content blocks
- Supports `tool_choice`: "auto", "any", tool name, or dict
- Arguments are objects, not JSON strings
- Supports parallel tool calls
- Supports `cache_control` for tool caching

### 10.3 Other Providers

- **Ollama**: Similar to OpenAI format
- **Groq**: Similar to OpenAI format
- **Fireworks**: Similar to OpenAI format
- **Mistral AI**: Similar to OpenAI format

Each may have slightly different tool_choice handling and parameter names.

---

## Summary

LangChain provides flexible tool definitions through:

1. **Multiple definition patterns**: `@tool` decorator, `BaseTool` class, Pydantic models
2. **Automatic schema generation**: From type hints and docstrings
3. **Universal binding**: `bind_tools()` works with all LLMs
4. **Standard tool calls**: Consistent `ToolCall` format across providers
5. **Complete integration**: From definition to execution in agent loops

The key to effective tool usage is:
- **Clear descriptions** for LLM decision-making
- **Detailed schemas** with type hints and field descriptions
- **Proper error handling** in tool implementations
- **Correct response formatting** with `ToolMessage`
- **Testing** both tools and agent loops
