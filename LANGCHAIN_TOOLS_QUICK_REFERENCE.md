# LangChain Tools - Quick Reference Card

## Tool Definition Quick Start

### Simple Tool (Recommended for Most Cases)
```python
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search the database for information."""
    return f"Results for {query}"
```

### Tool with Custom Schema
```python
from pydantic import BaseModel, Field
from langchain_core.tools import tool

class SearchInput(BaseModel):
    query: str = Field(..., description="What to search for")
    limit: int = Field(default=10, description="Max results")

@tool(args_schema=SearchInput)
def search(query: str, limit: int = 10) -> str:
    """Search with parameters."""
    return f"Results for {query}"
```

### Complex Tool (Class-Based)
```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "What this tool does"
    args_schema: type[BaseModel] = InputSchema
    
    def _run(self, **kwargs) -> str:
        return "result"
    
    async def _arun(self, **kwargs) -> str:
        return "result"
```

---

## Binding Tools to LLMs

### Basic Binding
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([tool1, tool2])
```

### With Tool Choice Control
```python
# Auto (let model decide)
model = llm.bind_tools([tool1, tool2])

# Force at least one tool
model = llm.bind_tools([tool1, tool2], tool_choice="any")

# Force specific tool
model = llm.bind_tools([tool1, tool2], tool_choice="tool1")

# Don't use tools
model = llm.bind_tools([tool1, tool2], tool_choice="none")
```

---

## Processing Tool Calls

### Extract Tool Calls from Response
```python
response = model.invoke("user query")

# Tool calls are in AIMessage
if response.tool_calls:
    for tool_call in response.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]
```

### Create Response Messages
```python
from langchain_core.messages import ToolMessage

# Execute tool
result = my_tool.invoke(args)

# Create response
tool_response = ToolMessage(
    content=result,           # Tool output
    tool_call_id=call_id,     # Match original call ID
    name=name                 # Tool name
)

# Add to messages
messages.append(response)
messages.append(tool_response)
```

---

## Agent Implementation

### With LangGraph (Recommended)
```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-3-sonnet-20240229")
agent = create_react_agent(llm, tools)

result = agent.invoke({
    "messages": [("user", "Your query")]
})
```

### Manual Agent Loop
```python
messages = [HumanMessage(content="query")]

while True:
    response = model.invoke(messages)
    messages.append(response)
    
    if not response.tool_calls:
        print(response.content)
        break
    
    for tc in response.tool_calls:
        result = execute_tool(tc["name"], tc["args"])
        messages.append(ToolMessage(
            content=result,
            tool_call_id=tc["id"],
            name=tc["name"]
        ))
```

---

## Tool Definition Patterns

| Pattern | Use Case | Complexity | Code |
|---------|----------|-----------|------|
| `@tool` decorator | Simple functions | Low | Single decorator |
| Pydantic BaseModel | Schema-first | Low-Medium | Class definition |
| BaseTool subclass | Complex logic | High | Custom class |

---

## Argument Types and Schema Generation

### Basic Types
```python
@tool
def example(
    text: str,              # JSON string
    number: int,            # JSON integer
    decimal: float,         # JSON number
    flag: bool,             # JSON boolean
    items: list[str],       # JSON array
    data: dict[str, int],   # JSON object
) -> str:
    """Generates correct JSON schema."""
    return "result"
```

### Optional Arguments
```python
from typing import Optional

@tool
def example(
    required: str,
    optional: Optional[str] = None,
    with_default: str = "default"
) -> str:
    """Parameters with defaults."""
    return "result"
```

### Enum Arguments
```python
from enum import Enum

class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

@tool
def paint(color: Color) -> str:
    """Pick from fixed choices."""
    return f"Painted {color.value}"
```

### Annotated with Descriptions
```python
from typing import Annotated

@tool
def example(
    query: Annotated[str, "The search query string"],
    limit: Annotated[int, "Max results (1-100)"]
) -> str:
    """Inline descriptions."""
    return "result"
```

---

## Error Handling

### Raise Tool Exception
```python
from langchain_core.tools import tool, ToolException

@tool
def safe_operation(param: str) -> str:
    """Handles errors properly."""
    try:
        if not param:
            raise ValueError("Param required")
        return process(param)
    except Exception as e:
        raise ToolException(f"Operation failed: {str(e)}")
```

### Validation in Schema
```python
from pydantic import field_validator

class Input(BaseModel):
    email: str
    
    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v
```

---

## Common Tool Patterns

### Search Tool
```python
@tool
def search_products(
    query: str,
    category: Optional[str] = None,
    sort_by: str = "relevance"
) -> str:
    """Search product database.
    
    Args:
        query: Product name or description
        category: Filter by category
        sort_by: 'relevance', 'price_low', 'price_high', 'rating'
    """
    return f"Results for {query}"
```

### Calculator Tool
```python
@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform arithmetic.
    
    Operations: add, subtract, multiply, divide
    """
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }
    result = ops[operation](a, b)
    return f"{a} {operation} {b} = {result}"
```

### API Call Tool
```python
@tool
async def fetch_api(url: str, method: str = "GET") -> str:
    """Fetch data from API."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url) as resp:
            return await resp.text()
```

---

## Tool Testing

### Basic Test
```python
def test_tool():
    result = my_tool.invoke({"param": "value"})
    assert result == "expected"
```

### Test Schema
```python
def test_tool_schema():
    assert my_tool.name == "my_tool"
    assert "param" in my_tool.args
    assert my_tool.description
```

### Mock LLM Test
```python
from unittest.mock import Mock
from langchain_core.messages import AIMessage

def test_with_mock():
    mock_llm = Mock()
    mock_llm.invoke.return_value = AIMessage(
        content="",
        tool_calls=[{
            "name": "my_tool",
            "args": {"param": "value"},
            "id": "123",
            "type": "tool_call"
        }]
    )
    
    model = mock_llm.bind_tools([my_tool])
    response = model.invoke("test")
    assert response.tool_calls[0]["name"] == "my_tool"
```

---

## Tool Choice Parameters

### OpenAI Format
```python
# Auto: Model decides
llm.bind_tools(tools)

# Force any tool
llm.bind_tools(tools, tool_choice="required")

# Force specific
llm.bind_tools(tools, tool_choice="tool_name")

# Or dict format
llm.bind_tools(tools, tool_choice={
    "type": "function",
    "function": {"name": "tool_name"}
})
```

### Anthropic Format
```python
# Auto
llm.bind_tools(tools)

# Force any
llm.bind_tools(tools, tool_choice="any")

# Force specific
llm.bind_tools(tools, tool_choice="tool_name")

# Or dict
llm.bind_tools(tools, tool_choice={
    "type": "tool",
    "name": "tool_name"
})
```

---

## Troubleshooting

### Tool Never Called
**Solution:** Make description more specific with examples
```python
# BAD
@tool
def search(query: str) -> str:
    """Search."""

# GOOD
@tool
def search_products(query: str) -> str:
    """Search product database for items by name or description.
    
    Use when user asks about products or wants to find items.
    """
```

### Wrong Arguments Passed
**Solution:** Add validation
```python
from pydantic import field_validator

class Input(BaseModel):
    param: int
    
    @field_validator("param")
    @classmethod
    def validate_param(cls, v):
        if v < 0:
            raise ValueError("Must be positive")
        return v
```

### Tool Not Found
**Solution:** Check tool name (case-sensitive)
```python
# Define
@tool(name="exact_name")
def my_function() -> str:
    pass

# Use exactly
model.bind_tools([my_function], tool_choice="exact_name")
```

### Invalid Arguments Error
**Solution:** Ensure all arguments are JSON serializable
```python
# BAD
@tool
def bad_tool(data: object) -> str:
    return str(data)

# GOOD
@tool
def good_tool(data: dict) -> str:
    return str(data)
```

---

## Best Practices Checklist

- [ ] Tool has clear, specific description with use cases
- [ ] All parameters have detailed descriptions
- [ ] Arguments are typed correctly for JSON schema generation
- [ ] Tool raises `ToolException` for errors
- [ ] Pydantic validation is used for complex inputs
- [ ] Tool returns string or JSON-serializable output
- [ ] Tool has been tested independently
- [ ] Tool timeout is reasonable for agent loop
- [ ] Error messages are helpful to the LLM
- [ ] Documentation has usage examples

---

## Useful Imports

```python
# Basic tools
from langchain_core.tools import tool, BaseTool, Tool

# Messages
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

# Schema
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated

# Agents
from langgraph.prebuilt import create_react_agent

# Error handling
from langchain_core.tools import ToolException

# Chat models
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
```

---

## Provider Compatibility

| Feature | OpenAI | Anthropic | Ollama | Groq | Fireworks |
|---------|--------|-----------|--------|------|-----------|
| Tool calling | ✓ | ✓ | ✓ | ✓ | ✓ |
| Parallel tools | ✗ | ✓ | ✗ | ✗ | ✗ |
| Tool caching | ✗ | ✓ | ✗ | ✗ | ✗ |
| Strict mode | ✓ | ✓ | ✗ | ✗ | ✗ |

---

## Additional Resources

- **Full Guide**: `LANGCHAIN_TOOLS_IMPLEMENTATION_GUIDE.md`
- **Code Examples**: `LANGCHAIN_TOOLS_CODE_EXAMPLES.md`
- **Architecture**: `LANGCHAIN_TOOLS_ARCHITECTURE_PATTERNS.md`
- **Research Summary**: `LANGCHAIN_TOOLS_RESEARCH_SUMMARY.md`
- **LangChain Docs**: https://python.langchain.com/docs/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
