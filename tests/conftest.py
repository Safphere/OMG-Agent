"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def llm_config():
    """LLM configuration fixture."""
    from omg_agent.core.agent.llm import LLMConfig

    return LLMConfig(
        api_base="http://localhost:8000/v1",
        model="autoglm-phone-9b",
        api_key="test-key",
    )


@pytest.fixture
def agent_config():
    """Agent configuration fixture."""
    from omg_agent.core.agent import AgentConfig

    return AgentConfig(device_id="test-device")


@pytest.fixture
def mock_screenshot():
    """Mock screenshot fixture."""
    from PIL import Image

    return Image.new("RGB", (1080, 2400), color="white")


@pytest.fixture
def mock_adb(monkeypatch):
    """Mock ADB subprocess calls."""
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=b""))
    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run
