"""System prompts for the agent."""

from .system import get_system_prompt, SYSTEM_PROMPT_ZH, SYSTEM_PROMPT_EN
from .autoglm import get_autoglm_prompt, AUTOGLM_PROMPT_ZH, AUTOGLM_PROMPT_EN
from .step import get_step_prompt, STEP_PROMPT_ZH

__all__ = [
    "get_system_prompt",
    "SYSTEM_PROMPT_ZH",
    "SYSTEM_PROMPT_EN",
    "get_autoglm_prompt",
    "AUTOGLM_PROMPT_ZH",
    "AUTOGLM_PROMPT_EN",
    "get_step_prompt",
    "STEP_PROMPT_ZH",
]
