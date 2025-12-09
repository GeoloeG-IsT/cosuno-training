# LangChain Tools Research Summary

## Research Completed

I have completed comprehensive research on LangChain's tool implementation system. The research covered:

1. **Tool Definition Mechanisms** - All approaches for defining tools in LangChain
2. **Tool Binding to LLMs** - How tools are attached to language models
3. **Tool Call Processing** - How LLM responses with tool calls are handled
4. **Agent Patterns** - AgentExecutor and modern LangGraph approaches
5. **Best Practices** - Guidelines for effective tool implementation

---

## Key Findings

### 1. Tool Definition Methods

LangChain provides **three primary patterns** for tool definition:

#### A. Decorator Pattern (`@tool`)
- **Simplest approach** - single decorator on function
- **Automatic schema inference** from function signature and docstring
- **Best for**: Simple utility functions
- **Overhead**: Minimal boilerplate

```python
@tool
def search(query: str) -> str:
    """Search for information."""
    return "results"
```

#### B. Class-Based Pattern (`BaseTool` subclass)
- **Most flexible** - full control over initialization and execution
- **Supports state** and custom validation
- **Requires** implementing `_run()` and `_arun()` methods
- **Best for**: Complex tools with initialization logic

```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "Description"
    args_schema: type[BaseModel] = InputSchema
    
    def _run(self, **kwargs) -> str:
        return "result"
```

#### C. Pydantic Model Pattern
- **Type-safe** - uses Pydantic for validation
- **Works directly with `bind_tools()`** without additional execution logic
- **Best for**: Schema-first design and structured output integration

```python
class GetWeather(BaseModel):
    """Get weather for location."""
    location: str = Field(..., description="City and state")

model = llm.bind_tools([GetWeather])
```

### 2. Schema Generation and Validation

**Key Points:**
- Schemas are **automatically generated** from type hints
- Docstrings are parsed for descriptions (use `parse_docstring=True`)
- Use `Annotated[type, "description"]` for inline parameter descriptions
- Pydantic validators are executed on arguments before tool execution
- **Critical**: `args_schema` must be typed as `type[BaseModel]`, not just `BaseModel`

**Schema Formats:**
- **JSON Schema**: Standard Python/JSON format
- **OpenAI Format**: `{"type": "function", "function": {...}}`
- **Anthropic Format**: `{"name": "...", "description": "...", "input_schema": {...}}`

### 3. Tool Binding to LLMs

**Method**: `llm.bind_tools(tools, tool_choice=...)`

**Supported Tool Formats:**
1. Pydantic `BaseModel` classes
2. `BaseTool` instances
3. Functions with type hints
4. Pre-built tool dicts

**Tool Choice Parameter:**
- `"auto"`: Model decides if tool is needed (default)
- `"any"` or `"required"`: Force at least one tool call
- `"tool_name"`: Force specific tool
- `None` or `"none"`: Don't call tools
- Dict format for provider-specific configuration

```python
# Auto (let model decide)
model = llm.bind_tools([tool1, tool2])

# Force any tool
model = llm.bind_tools([tool1, tool2], tool_choice="any")

# Force specific tool
model = llm.bind_tools([tool1, tool2], tool_choice="tool1")

# OpenAI dict format
model = llm.bind_tools(
    [tool1], 
    tool_choice={"type": "function", "function": {"name": "tool1"}}
)
```

### 4. Tool Call Processing from LLM Responses

**Structure**: Tool calls are available in `AIMessage.tool_calls` field

**ToolCall TypedDict:**
```python
{
    "name": str,              # Tool name
    "args": dict,             # Arguments as dictionary
    "id": str,                # Unique identifier
    "type": "tool_call"       # Literal
}
```

**Response Pattern:**
```python
response = model.invoke(messages)

for tool_call in response.tool_calls:
    # Execute tool
    result = execute_tool(
        tool_call["name"],
        tool_call["args"]
    )
    
    # Create response message
    tool_msg = ToolMessage(
        content=result,
        tool_call_id=tool_call["id"],
        name=tool_call["name"]
    )
    
    # Continue conversation
    messages.append(response)
    messages.append(tool_msg)
```

**Handling Invalid Calls:**
- Check `response.invalid_tool_calls` for failed parsing
- Contains original arguments and error messages
- Agent can retry or request clarification

### 5. Tool Execution in Agents

**Classic Pattern (AgentExecutor - Deprecated):**
```python
from langchain_classic.agents import initialize_agent

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)
agent.run("query")
```

**Modern Pattern (LangGraph - Recommended):**
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(llm, tools)
result = agent.invoke({
    "messages": [("user", "query")]
})
```

**Agent Loop Flow:**
1. User sends query
2. Model (with bound tools) processes
3. If tool_calls in response:
   - Extract and execute each tool call
   - Package results in ToolMessage
   - Add to message history
   - Re-invoke model
4. If no tool_calls:
   - Return final response

### 6. Best Practices

#### A. Clear Tool Descriptions
```python
# BAD - Too vague
@tool
def search(query: str) -> str:
    """Search."""
    return "result"

# GOOD - Specific and actionable
@tool
def search_product_database(query: str) -> str:
    """Search the product database by name, category, or features.
    
    Use this when user asks about products or want to find items.
    """
    return "result"
```

#### B. Detailed Parameter Descriptions
```python
class SearchInput(BaseModel):
    query: str = Field(
        ...,
        description="Search term - can be product name, category like 'electronics'"
    )
    max_results: int = Field(
        default=10,
        description="Maximum results to return (1-100)"
    )
```

#### C. Proper Error Handling
```python
from langchain_core.tools import ToolException

@tool
def risky_operation(param: str) -> str:
    """Operation that might fail."""
    try:
        return process(param)
    except ValueError as e:
        raise ToolException(f"Invalid input: {str(e)}")
```

#### D. Validation in Schema
```python
from pydantic import field_validator

class Input(BaseModel):
    email: str
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
```

#### E. Rich Documentation
```python
@tool
def calculate_tax(amount: float, rate: float = 0.08) -> str:
    """Calculate tax on purchase amount.
    
    Examples:
    - $100 with 8% tax = $108 total
    - $1000 with 6% tax = $1060 total
    
    Use when user asks about taxes or totals with tax.
    """
    return f"${amount * (1 + rate):.2f}"
```

### 7. Provider-Specific Details

**OpenAI:**
- Function tool type
- tool_choice: "auto", "none", "required", tool name, or dict
- Arguments as JSON strings inside schema

**Anthropic:**
- Tool use content blocks
- tool_choice: "auto", "any", tool name, or dict format
- Arguments as objects
- Supports parallel tool calls
- Supports tool caching with `cache_control`

**Other Providers (Ollama, Groq, Fireworks, Mistral):**
- Generally OpenAI-compatible format
- May have minor parameter name differences
- Check provider documentation for specifics

### 8. Common Pitfalls and Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Tool never called | Unclear description | Make description specific with examples |
| Wrong arguments | Missing validation | Add Pydantic validators |
| Parse failures | Invalid JSON | Use `partial=True` for streaming |
| Tool not found | Name mismatch | Ensure exact name matching (case-sensitive) |
| Schema errors | Wrong type annotation | Use `args_schema: type[BaseModel]` |
| No response | Tool didn't execute | Check if tool raises exception properly |

---

## Documents Created

### 1. **LANGCHAIN_TOOLS_IMPLEMENTATION_GUIDE.md**
Comprehensive guide covering:
- All tool definition patterns with examples
- Tool binding to LLMs
- Tool call processing from responses
- AgentExecutor and LangGraph patterns
- Best practices and patterns
- Provider-specific notes
- Common issues and solutions

### 2. **LANGCHAIN_TOOLS_CODE_EXAMPLES.md**
15 practical, runnable code examples:
1. Basic tool definition
2. Tool with Pydantic schema
3. Multiple tools with tool_choice
4. BaseTool subclass
5. Complete agent loop
6. Tool with validation
7. Tool with error handling
8. Tool with rich output
9. Dynamic tool creation
10. Async tools
11. Tools with callbacks
12. Tool testing
13. Pydantic models as tools
14. Tools with examples in descriptions
15. Tool composition with Runnable

### 3. **LANGCHAIN_TOOLS_ARCHITECTURE_PATTERNS.md**
Advanced architecture and design patterns:
- Tool system architecture overview
- Tool definition patterns (decorator, class, model)
- Schema design patterns (flat, nested, enum)
- Tool execution patterns (direct, async, streaming)
- Tool integration patterns (single, multi, dependency graph)
- Error handling patterns (exceptions, fallbacks, retries)
- Validation patterns (Pydantic, custom)
- Performance patterns (caching, rate limiting, batching)
- Testing patterns (unit, integration, end-to-end)
- Monitoring and observability patterns

---

## Quick Reference

### Define a Tool
```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Tool description."""
    return "result"
```

### Bind to LLM
```python
model = llm.bind_tools([my_tool])
```

### Handle Tool Calls
```python
response = model.invoke("user query")

for tool_call in response.tool_calls:
    result = execute_tool(tool_call["name"], tool_call["args"])
    messages.append(ToolMessage(
        content=result,
        tool_call_id=tool_call["id"],
        name=tool_call["name"]
    ))
```

### Create Agent
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(llm, tools)
result = agent.invoke({"messages": [("user", "query")]})
```

---

## Key Takeaways

1. **Use `@tool` decorator** for simple tools - it's the cleanest approach
2. **Use `BaseTool` subclass** for complex tools needing state or custom logic
3. **Clear descriptions matter** - LLMs use them to decide when to call tools
4. **Type hints are converted to schemas** - use them liberally for validation
5. **Always handle tool errors** - raise `ToolException` for agent to manage
6. **Process `tool_calls` with `ToolMessage`** - maintains conversation context
7. **Use LangGraph** for agents - AgentExecutor is deprecated
8. **Test tools independently** - before integrating with agents

---

## Resources Used

All information sourced from official LangChain GitHub repository:
- `langchain_core/tools/` - Core tool implementation
- `langchain_core/messages/tool.py` - ToolCall and ToolMessage definitions
- `langchain_core/output_parsers/openai_tools.py` - Tool call parsing
- Partner implementations (Anthropic, OpenAI, Mistral, etc.) - Provider integration
- Test files - Real-world usage examples

---

## Next Steps

1. **Review the implementation guide** for conceptual understanding
2. **Study the code examples** for practical patterns
3. **Apply architecture patterns** to your specific use case
4. **Test tools independently** before agent integration
5. **Monitor tool execution** in production with callbacks and logging
