"""
Action Space Definition - Unified action types for phone automation.

Combines action types from Open-AutoGLM and gelab-zero:
- Touch actions: CLICK, DOUBLE_TAP, LONG_PRESS
- Gesture actions: SWIPE
- Input actions: TYPE
- Navigation: BACK, HOME, LAUNCH
- Control flow: WAIT, INFO, COMPLETE, ABORT
- Special: TAKE_OVER (human intervention)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class ActionType(str, Enum):
    """Enumeration of all supported action types."""

    # Touch actions
    CLICK = "CLICK"
    DOUBLE_TAP = "DOUBLE_TAP"
    LONG_PRESS = "LONG_PRESS"

    # Gesture actions
    SWIPE = "SWIPE"

    # Input actions
    TYPE = "TYPE"

    # Navigation actions
    BACK = "BACK"
    HOME = "HOME"
    LAUNCH = "LAUNCH"  # aka AWAKE in gelab-zero

    # Control flow actions
    WAIT = "WAIT"
    INFO = "INFO"  # Ask user for information
    COMPLETE = "COMPLETE"  # Task completed successfully
    ABORT = "ABORT"  # Task cannot be completed

    # Special actions
    TAKE_OVER = "TAKE_OVER"  # Request human intervention
    NOTE = "NOTE"  # Record information (internal use)


class Direction(str, Enum):
    """Swipe direction enum."""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class HotKey(str, Enum):
    """System hot keys."""
    ENTER = "ENTER"
    BACK = "BACK"
    HOME = "HOME"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    POWER = "POWER"


class CompletionStatus(str, Enum):
    """Task completion status."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass
class Point:
    """
    Normalized point coordinates (0-1000 range).

    Using 0-1000 range provides integer precision while being
    resolution-independent. To convert to actual pixels:
        actual_x = point.x * screen_width / 1000
        actual_y = point.y * screen_height / 1000
    """
    x: int
    y: int

    def __post_init__(self):
        if not (0 <= self.x <= 1000 and 0 <= self.y <= 1000):
            raise ValueError(f"Point coordinates must be in range [0, 1000], got ({self.x}, {self.y})")

    def to_absolute(self, width: int, height: int) -> tuple[int, int]:
        """Convert to absolute pixel coordinates."""
        return (
            int(self.x * width / 1000),
            int(self.y * height / 1000)
        )

    @classmethod
    def from_absolute(cls, x: int, y: int, width: int, height: int) -> "Point":
        """Create from absolute pixel coordinates."""
        return cls(
            x=int(x * 1000 / width),
            y=int(y * 1000 / height)
        )

    @classmethod
    def from_list(cls, coords: list[int]) -> "Point":
        """Create from [x, y] list."""
        return cls(x=coords[0], y=coords[1])

    def to_list(self) -> list[int]:
        """Convert to [x, y] list."""
        return [self.x, self.y]


@dataclass
class Action:
    """
    Base action class with common fields.

    All actions have:
    - action_type: The type of action
    - thinking: The reasoning behind the action (CoT)
    - explanation: Brief description of what the action does
    - summary: Summary of history after this action (optional)
    """
    action_type: ActionType
    thinking: str = ""
    explanation: str = ""
    summary: str = ""

    # Additional fields based on action type
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert action to dictionary."""
        result = {
            "action_type": self.action_type.value,
            "thinking": self.thinking,
            "explanation": self.explanation,
        }
        if self.summary:
            result["summary"] = self.summary
        result.update(self.params)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        """Create action from dictionary."""
        action_type = ActionType(data.get("action_type") or data.get("action"))
        thinking = data.get("thinking", data.get("cot", ""))
        explanation = data.get("explanation", data.get("explain", ""))
        summary = data.get("summary", "")

        # Extract params
        reserved_keys = {"action_type", "action", "thinking", "cot", "explanation", "explain", "summary"}
        params = {k: v for k, v in data.items() if k not in reserved_keys}

        return cls(
            action_type=action_type,
            thinking=thinking,
            explanation=explanation,
            summary=summary,
            params=params
        )


class ActionSpace:
    """
    Defines and validates the action space for phone automation.

    Provides validation and documentation for all action types.
    """

    # Required parameters for each action type
    REQUIRED_PARAMS: dict[ActionType, list[str]] = {
        ActionType.CLICK: ["point"],
        ActionType.DOUBLE_TAP: ["point"],
        ActionType.LONG_PRESS: ["point"],
        ActionType.SWIPE: [],  # Either (point1, point2) or (point, direction)
        ActionType.TYPE: ["value"],
        ActionType.BACK: [],
        ActionType.HOME: [],
        ActionType.LAUNCH: ["value"],  # app name
        ActionType.WAIT: ["value"],  # duration in seconds
        ActionType.INFO: ["value"],  # question to ask
        ActionType.COMPLETE: [],  # optional: return message
        ActionType.ABORT: [],  # optional: reason
        ActionType.TAKE_OVER: [],  # optional: message
        ActionType.NOTE: ["value"],
    }

    # Optional parameters for each action type
    OPTIONAL_PARAMS: dict[ActionType, list[str]] = {
        ActionType.CLICK: ["message"],  # For sensitive operation confirmation
        ActionType.LONG_PRESS: ["duration"],
        ActionType.SWIPE: ["duration"],
        ActionType.TYPE: ["point", "keyboard_exists"],  # point for where to tap first
        ActionType.COMPLETE: ["return", "status"],
        ActionType.ABORT: ["value", "reason"],
        ActionType.TAKE_OVER: ["message"],
    }

    @classmethod
    def validate(cls, action: Action) -> tuple[bool, str]:
        """
        Validate an action against the action space definition.

        Returns:
            (is_valid, error_message)
        """
        action_type = action.action_type
        params = action.params

        # Check required parameters
        required = cls.REQUIRED_PARAMS.get(action_type, [])
        for param in required:
            if param not in params:
                return False, f"Missing required parameter '{param}' for {action_type.value}"

        # Special validation for SWIPE
        if action_type == ActionType.SWIPE:
            has_two_points = "point1" in params and "point2" in params
            has_point_direction = "point" in params and "direction" in params
            if not (has_two_points or has_point_direction):
                return False, "SWIPE requires either (point1, point2) or (point, direction)"

        # Validate point coordinates
        point_params = ["point", "point1", "point2"]
        for param_name in point_params:
            if param_name in params:
                point = params[param_name]
                if isinstance(point, (list, tuple)):
                    if len(point) != 2:
                        return False, f"Point {param_name} must have 2 coordinates"
                    if not all(isinstance(v, int) and 0 <= v <= 1000 for v in point):
                        return False, f"Point {param_name} coordinates must be integers in [0, 1000]"

        return True, ""

    @classmethod
    def get_prompt(cls, lang: str = "zh") -> str:
        """Get action space prompt for LLM."""
        if lang == "zh":
            return cls._get_chinese_prompt()
        return cls._get_english_prompt()

    @classmethod
    def _get_chinese_prompt(cls) -> str:
        return """# Action Space (动作空间)

在 Android 手机场景下，你的动作空间包含以下操作类型。所有坐标使用归一化坐标系 (0-1000)。

1. CLICK: 点击屏幕坐标
   格式: action:CLICK  point:x,y

2. DOUBLE_TAP: 双击屏幕坐标
   格式: action:DOUBLE_TAP  point:x,y

3. LONG_PRESS: 长按屏幕坐标
   格式: action:LONG_PRESS  point:x,y  duration:秒数(可选)

4. SWIPE: 滑动屏幕
   格式: action:SWIPE  point1:x1,y1  point2:x2,y2
   或: action:SWIPE  point:x,y  direction:UP/DOWN/LEFT/RIGHT

5. TYPE: 输入文字
   格式: action:TYPE  value:输入内容  point:x,y(可选,输入框位置)

6. BACK: 按返回键
   格式: action:BACK

7. HOME: 按主页键
   格式: action:HOME

8. LAUNCH: 启动应用
   格式: action:LAUNCH  value:应用名称

9. WAIT: 等待
   格式: action:WAIT  value:等待秒数

10. INFO: 向用户询问信息
    格式: action:INFO  value:问题内容

11. COMPLETE: 任务完成
    格式: action:COMPLETE  return:完成报告(可选)

12. ABORT: 终止任务
    格式: action:ABORT  value:终止原因

输出格式:
<THINK>思考过程</THINK>
explain:动作说明  action:动作类型  参数...  summary:历史总结
"""

    @classmethod
    def _get_english_prompt(cls) -> str:
        return """# Action Space

For Android phone automation, your action space includes the following types. All coordinates use normalized coordinate system (0-1000).

1. CLICK: Tap screen coordinate
   Format: action:CLICK  point:x,y

2. DOUBLE_TAP: Double tap screen coordinate
   Format: action:DOUBLE_TAP  point:x,y

3. LONG_PRESS: Long press screen coordinate
   Format: action:LONG_PRESS  point:x,y  duration:seconds(optional)

4. SWIPE: Swipe screen
   Format: action:SWIPE  point1:x1,y1  point2:x2,y2
   Or: action:SWIPE  point:x,y  direction:UP/DOWN/LEFT/RIGHT

5. TYPE: Input text
   Format: action:TYPE  value:text_content  point:x,y(optional)

6. BACK: Press back button
   Format: action:BACK

7. HOME: Press home button
   Format: action:HOME

8. LAUNCH: Launch app
   Format: action:LAUNCH  value:app_name

9. WAIT: Wait for duration
   Format: action:WAIT  value:seconds

10. INFO: Ask user for information
    Format: action:INFO  value:question

11. COMPLETE: Task completed
    Format: action:COMPLETE  return:completion_message(optional)

12. ABORT: Abort task
    Format: action:ABORT  value:reason

Output format:
<THINK>reasoning process</THINK>
explain:action_description  action:action_type  params...  summary:history_summary
"""
