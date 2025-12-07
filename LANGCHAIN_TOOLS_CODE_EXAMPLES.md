# LangChain Tools - Practical Code Examples

This file contains complete, runnable examples demonstrating LangChain tool patterns.

## 1. Basic Tool Definition and Usage

```python
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

# Define a simple tool
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.
    
    Args:
        location: The city and state, e.g., 'San Francisco, CA'
    """
    # In reality, this would call a weather API
    temperatures = {
        "san francisco": "65°F",
        "new york": "45°F",
        "los angeles": "72°F"
    }
    return temperatures.get(location.lower(), "Unknown location")

# Bind to LLM
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model_with_tools = llm.bind_tools([get_weather])

# Use the tool
response = model_with_tools.invoke("What's the weather in San Francisco?")
print(f"Response: {response}")
print(f"Tool calls: {response.tool_calls}")
```

## 2. Tool with Pydantic Schema

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic

class WeatherInput(BaseModel):
    """Input for weather tool."""
    location: str = Field(..., description="City and state, e.g., 'San Francisco, CA'")
    units: str = Field(
        default="fahrenheit",
        description="Temperature units: 'fahrenheit' or 'celsius'"
    )

@tool(args_schema=WeatherInput)
def get_detailed_weather(location: str, units: str = "fahrenheit") -> str:
    """Get weather with specified units."""
    temp = "65" if location.lower() == "san francisco" else "45"
    unit_symbol = "°F" if units == "fahrenheit" else "°C"
    return f"{temp}{unit_symbol}"

# Use
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model = llm.bind_tools([get_detailed_weather])
response = model.invoke("Get weather in San Francisco in Celsius")
```

## 3. Multiple Tools with Tool Choice

```python
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

@tool
def search_database(query: str) -> str:
    """Search the product database."""
    return f"Found 5 products matching '{query}'"

@tool
def calculate(operation: str, a: float, b: float) -> str:
    """Perform calculations."""
    if operation == "add":
        return str(a + b)
    elif operation == "multiply":
        return str(a * b)
    return "Unknown operation"

@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {recipient}"

# Bind all tools
llm = ChatAnthropic(model="claude-3-sonnet-20240229")

# Auto: model decides
model_auto = llm.bind_tools(
    [search_database, calculate, send_email],
    tool_choice="auto"
)

# Any: force at least one tool
model_any = llm.bind_tools(
    [search_database, calculate, send_email],
    tool_choice="any"
)

# Specific: force particular tool
model_specific = llm.bind_tools(
    [search_database, calculate, send_email],
    tool_choice="calculate"
)
```

## 4. BaseTool Subclass

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional

class DatabaseSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    filters: Optional[dict] = Field(None, description="Filter criteria")

class DatabaseSearchTool(BaseTool):
    """Custom database search tool."""
    
    name: str = "database_search"
    description: str = (
        "Search the product database for items matching criteria. "
        "Use this when user wants to find products."
    )
    args_schema: type[BaseModel] = DatabaseSearchInput
    
    def _run(self, query: str, filters: Optional[dict] = None) -> str:
        """Execute the search."""
        # Real implementation would query a database
        result = f"Results for '{query}'"
        if filters:
            result += f" with filters {filters}"
        return result
    
    async def _arun(self, query: str, filters: Optional[dict] = None) -> str:
        """Async execution."""
        # Async implementation
        return self._run(query, filters)

# Use
tool = DatabaseSearchTool()
result = tool.invoke({"query": "laptop", "filters": {"price": "<1000"}})
print(result)
```

## 5. Complete Agent Loop

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    # Simulate search
    if "capital" in query.lower():
        return "Paris is the capital of France"
    return "No results found"

@tool
def calculate(a: int, b: int, operation: str = "add") -> str:
    """Perform calculations."""
    if operation == "add":
        return str(a + b)
    elif operation == "multiply":
        return str(a * b)
    return "Unknown operation"

def run_agent(query: str):
    """Run agent loop."""
    llm = ChatAnthropic(model="claude-3-sonnet-20240229")
    model = llm.bind_tools([search, calculate])
    
    # Initialize messages
    messages = [HumanMessage(content=query)]
    
    print(f"User: {query}\n")
    
    # Agent loop
    while True:
        # Get response
        response = model.invoke(messages)
        messages.append(response)
        
        # Check if done
        if not response.tool_calls:
            print(f"Assistant: {response.content}")
            break
        
        # Process tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f"Using tool: {tool_name}")
            print(f"Arguments: {tool_args}\n")
            
            # Execute tool
            if tool_name == "search":
                result = search.invoke(tool_args)
            elif tool_name == "calculate":
                result = calculate.invoke(tool_args)
            else:
                result = "Tool not found"
            
            # Add tool response
            messages.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_name
            ))

# Run
run_agent("What is the capital of France?")
run_agent("What is 10 times 5?")
```

## 6. Tool with Validation

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

class EmailInput(BaseModel):
    """Email parameters."""
    recipient: str = Field(..., description="Email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    
    @field_validator("recipient")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email address")
        return v.lower()
    
    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v):
        if len(v) < 3:
            raise ValueError("Subject too short")
        return v

@tool(args_schema=EmailInput)
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email with validation."""
    return f"Email sent to {recipient}"

# Test validation
try:
    result = send_email.invoke({
        "recipient": "invalid-email",
        "subject": "Hi",
        "body": "Hello"
    })
except Exception as e:
    print(f"Error: {e}")

# Valid call
result = send_email.invoke({
    "recipient": "user@example.com",
    "subject": "Hello",
    "body": "How are you?"
})
print(result)
```

## 7. Tool with Error Handling

```python
from langchain_core.tools import tool, ToolException

@tool
def divide(a: float, b: float) -> str:
    """Divide two numbers."""
    try:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        return f"{a} / {b} = {result}"
    except ValueError as e:
        # Raise ToolException for agent to handle
        raise ToolException(f"Division failed: {str(e)}")

# Test error handling
try:
    result = divide.invoke({"a": 10, "b": 0})
except ToolException as e:
    print(f"Tool error: {e}")

# Valid call
result = divide.invoke({"a": 10, "b": 2})
print(result)
```

## 8. Tool with Rich Output

```python
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
import json

@tool
def analyze_data(data: list[float]) -> str:
    """Analyze numerical data."""
    if not data:
        return "No data provided"
    
    # Calculate statistics
    stats = {
        "count": len(data),
        "sum": sum(data),
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data)
    }
    
    # Return as JSON string
    return json.dumps(stats)

@tool
def analyze_data_with_artifact(data: list[float]) -> ToolMessage:
    """Analyze data returning both content and artifact."""
    stats = {
        "count": len(data),
        "sum": sum(data),
        "mean": sum(data) / len(data),
    }
    
    # Return with artifact for non-LLM use
    return ToolMessage(
        content=f"Analyzed {len(data)} data points",
        artifact=stats,
        tool_call_id="call_123",
        name="analyze_data_with_artifact"
    )

# Use
result = analyze_data.invoke({"data": [1, 2, 3, 4, 5]})
print(result)
```

## 9. Dynamic Tool Creation

```python
from langchain_core.tools import tool
from typing import Callable

def create_arithmetic_tool(operation: str) -> Callable:
    """Create an arithmetic tool dynamically."""
    
    @tool(name=f"arithmetic_{operation}")
    def arithmetic_tool(a: float, b: float) -> str:
        """Perform arithmetic operation."""
        if operation == "add":
            return str(a + b)
        elif operation == "subtract":
            return str(a - b)
        elif operation == "multiply":
            return str(a * b)
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            return str(a / b)
        return "Unknown operation"
    
    return arithmetic_tool

# Create tools dynamically
tools = []
for op in ["add", "subtract", "multiply", "divide"]:
    tools.append(create_arithmetic_tool(op))

# Use
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model = llm.bind_tools(tools)
response = model.invoke("Calculate 10 + 5")
print(response.tool_calls)
```

## 10. Async Tool

```python
import asyncio
from langchain_core.tools import tool

@tool
async def fetch_data(url: str) -> str:
    """Fetch data from URL asynchronously."""
    # Simulate async operation
    await asyncio.sleep(1)
    return f"Data from {url}"

# Test async
async def test_async():
    result = await fetch_data.ainvoke({"url": "https://example.com"})
    print(result)

# Run
# asyncio.run(test_async())
```

## 11. Tool with Callbacks

```python
from langchain_core.tools import tool
from langchain_core.callbacks import CallbackManagerForToolRun
from typing import Optional

@tool
def process_with_callback(
    data: str,
    run_manager: Optional[CallbackManagerForToolRun] = None
) -> str:
    """Process data with callbacks."""
    if run_manager:
        run_manager.on_text(f"Starting processing of: {data}")
    
    # Process
    result = data.upper()
    
    if run_manager:
        run_manager.on_text(f"Processing complete: {result}")
    
    return result
```

## 12. Tool Testing

```python
import pytest
from langchain_core.tools import tool

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def test_add_numbers():
    """Test the add_numbers tool."""
    # Test positive
    assert add_numbers.invoke({"a": 2, "b": 3}) == 5
    
    # Test negative
    assert add_numbers.invoke({"a": -1, "b": 1}) == 0
    
    # Test zeros
    assert add_numbers.invoke({"a": 0, "b": 0}) == 0

def test_tool_metadata():
    """Test tool metadata."""
    assert add_numbers.name == "add_numbers"
    assert "Add two numbers" in add_numbers.description
    assert "a" in add_numbers.args
    assert "b" in add_numbers.args

# Run tests
if __name__ == "__main__":
    test_add_numbers()
    test_tool_metadata()
    print("All tests passed!")
```

## 13. Using Pydantic Models as Tool Definitions

```python
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic

class SearchInput(BaseModel):
    """Search tool input."""
    query: str = Field(..., description="The search query")
    limit: int = Field(default=10, description="Max results")

class CalculatorInput(BaseModel):
    """Calculator tool input."""
    operation: str = Field(..., description="add, subtract, multiply, or divide")
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")

# Use Pydantic models directly as tools
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
model = llm.bind_tools([SearchInput, CalculatorInput])

response = model.invoke("Search for python tutorials")
print(response.tool_calls)
```

## 14. Tool with Examples in Description

```python
from langchain_core.tools import tool

@tool
def calculate_tax(amount: float, tax_rate: float = 0.08) -> str:
    """Calculate tax on an amount.
    
    Use this tool to calculate sales tax, income tax, or any percentage-based tax.
    
    Examples:
    - Product price $100 with 8% tax: total is $108
    - Income $50,000 with 20% tax: tax owed is $10,000
    - Service fee $500 with 6% tax: total is $530
    
    Args:
        amount: The base amount before tax
        tax_rate: The tax rate as decimal (0.08 = 8%)
    """
    tax = amount * tax_rate
    total = amount + tax
    return f"Amount: ${amount:.2f}, Tax (${tax_rate*100}%): ${tax:.2f}, Total: ${total:.2f}"

# Use
result = calculate_tax.invoke({"amount": 100, "tax_rate": 0.08})
print(result)
```

## 15. Tool Composition with Runnable

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tools import tool

# Create extraction tool
@tool
def extract_numbers(text: str) -> str:
    """Extract all numbers from text."""
    numbers = [c for c in text if c.isdigit()]
    return ",".join(numbers) if numbers else "No numbers found"

# Create analysis tool
def analyze_numbers(numbers_str: str) -> str:
    """Analyze extracted numbers."""
    if not numbers_str or numbers_str == "No numbers found":
        return "No numbers to analyze"
    
    numbers = [int(n) for n in numbers_str.split(",")]
    return f"Found {len(numbers)} numbers: sum={sum(numbers)}"

# Compose
extract_runnable = RunnableLambda(
    lambda x: extract_numbers.invoke({"text": x})
)
analysis_runnable = RunnableLambda(analyze_numbers)
pipeline = extract_runnable | analysis_runnable

# Convert to tool
text_analyzer = pipeline.as_tool(
    name="analyze_text",
    description="Extract and analyze numbers from text"
)

# Use
result = text_analyzer.invoke({"text": "I have 5 apples and 3 oranges"})
print(result)
```

These examples demonstrate the key patterns for working with tools in LangChain.
Each example is self-contained and can be run independently (with appropriate
environment setup and API keys for LLM calls).
