# Development Guide

<p align="center">
  <a href="development.md">English</a> | <a href="development_zh.md">中文</a>
</p>

## Environment Setup

```bash
# Clone Repository
git clone https://github.com/safphere/OMG-Agent.git
cd OMG-Agent

# Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install Dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Project Structure

```
OMG-Agent/
├── omg_agent/
│   ├── __init__.py
│   ├── __main__.py          # Entry Point
│   ├── gui/
│   │   ├── main_window.py   # Main Window
│   │   ├── widgets.py       # Custom Widgets
│   │   └── themes.py        # Themes
│   └── core/
│       ├── agent/           # AI Agent Core
│       │   ├── phone_agent.py    # Main Agent Class
│       │   ├── actions/          # Action Space
│       │   │   ├── space.py      # Action Definitions
│       │   │   ├── parser.py     # Parser
│       │   │   └── handler.py    # Handler
│       │   ├── device/           # Device Interaction
│       │   │   ├── screenshot.py # Screenshot
│       │   │   └── apps.py       # App Mapping
│       │   ├── llm/              # LLM Client
│       │   │   ├── client.py     # API Client
│       │   │   └── message.py    # Message Builder
│       │   ├── prompts/          # Prompts
│       │   ├── history.py        # History Management
│       │   └── session.py        # Session Management
│       ├── config.py        # Config Management
│       ├── i18n.py          # Internationalization
├── assets/                  # Assets
├── docs/                    # Documentation
├── tests/                   # Tests
└── run.py                   # Launch Script
```

## Core Modules

### PhoneAgent

Main Agent class, responsible for task execution loop:

```python
from omg_agent.core.agent import PhoneAgent, AgentConfig
from omg_agent.core.agent.llm import LLMConfig

# Config
llm_config = LLMConfig(
    api_base="http://localhost:8000/v1",
    model="autoglm-phone-9b"
)

agent_config = AgentConfig(
    device_id="emulator-5554",
    max_steps=100
)

# Create Agent
agent = PhoneAgent(llm_config, agent_config)

# Execute tasks
result = agent.run("Open WeChat")
print(result.message)
```

### ActionSpace

13 Action Types:

- `CLICK` - Click
- `DOUBLE_TAP` - Double Tap
- `LONG_PRESS` - Long Press
- `SWIPE` - Swipe
- `TYPE` - Type
- `BACK` - Go Back
- `HOME` - Go Home
- `LAUNCH` - Launch App
- `WAIT` - Wait
- `INFO` - Ask User
- `COMPLETE` - Complete
- `ABORT` - Abort
- `TAKE_OVER` - Request Takeover

### LLMClient

OpenAI-compatible LLM Client:

```python
from omg_agent.core.agent.llm import LLMClient, LLMConfig

client = LLMClient(LLMConfig(
    api_base="http://localhost:8000/v1",
    model="autoglm-phone-9b"
))

response = client.request([
    {"role": "user", "content": "Hello"}
])
print(response.content)
```

## Code Guidelines

```bash
# Formatting
black omg_agent/
isort omg_agent/

# Type Checking
mypy omg_agent/

# Linting
ruff check omg_agent/
```

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_agent.py

# Coverage
pytest --cov=omg_agent
```

## Adding New Actions

1. Add ActionType in `actions/space.py`:
```python
class ActionType(str, Enum):
    MY_ACTION = "MY_ACTION"
```

2. Add handler in `actions/handler.py`:
```python
def _handle_my_action(self, action: Action) -> ActionResult:
    # Implementation
    return ActionResult(success=True, should_finish=False)
```

3. Update `REQUIRED_PARAMS` and `OPTIONAL_PARAMS`.

## Adding New Language

1. Add field to `Strings` class in `core/i18n.py`.
2. Create new language config (refer to existing ones).
3. Register in `_LANGUAGES` dictionary.

## Release

```bash
# Build
python -m build

# Upload to PyPI
twine upload dist/*
```
