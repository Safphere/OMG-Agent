"""
OMG-Agent 核心模块

提供配置管理、设备控制等核心功能
"""

from omg_agent.core.config import Config, load_config, save_config, HISTORY_DIR
from omg_agent.core.i18n import I18n, get_text
from omg_agent.core.task_history import (
    TaskHistoryManager,
    TaskRecord,
    TaskStep,
    get_history_manager,
)

__all__ = [
    "Config", "load_config", "save_config", "HISTORY_DIR",
    "I18n", "get_text",
    "TaskHistoryManager", "TaskRecord", "TaskStep", "get_history_manager",
]
