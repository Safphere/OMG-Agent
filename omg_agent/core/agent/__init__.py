"""
Agent - A unified phone automation agent framework.

Combines the best features from Open-AutoGLM and gelab-zero:
- Clean architecture with clear separation of concerns
- Rich action space with INFO, ABORT, COMPLETE support
- Session management for task resumption
- History summary compression for efficient context management
- Task planning for complex multi-step tasks
- Callback mechanisms for human intervention
- Multi-model LLM support
"""

from .phone_agent import PhoneAgent, AgentConfig, StepResult, RunResult, ReplyMode
from .actions import ActionSpace, ActionHandler, ActionResult, ActionParser
from .actions.space import Action, ActionType, Point
from .history import HistoryManager, ConversationHistory
from .session import SessionManager, SessionState
from .planner import TaskPlanner, TaskPlan, SubTask, TaskStatus, analyze_task_complexity
from .llm import LLMConfig, ModelConfig, LLMClient
from .device import Screenshot, get_screenshot, take_screenshot

__version__ = "0.1.0"
__all__ = [
    # Main agent
    "PhoneAgent",
    "AgentConfig",
    "StepResult",
    "RunResult",
    "ReplyMode",
    # LLM
    "LLMConfig",
    "ModelConfig",  # Alias for backward compatibility
    "LLMClient",
    # Actions
    "ActionSpace",
    "ActionHandler",
    "ActionResult",
    "ActionParser",
    "Action",
    "ActionType",
    "Point",
    # Device
    "Screenshot",
    "get_screenshot",
    "take_screenshot",
    # History
    "HistoryManager",
    "ConversationHistory",
    # Session
    "SessionManager",
    "SessionState",
    # Planner
    "TaskPlanner",
    "TaskPlan",
    "SubTask",
    "TaskStatus",
    "analyze_task_complexity",
]

