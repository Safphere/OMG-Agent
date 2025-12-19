"""
Action Handler - Execute actions on Android device.

Supports multiple execution backends:
1. Direct ADB commands
2. MCP tools (if available)
"""

import time
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .space import Action, ActionType, Point, Direction


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    should_finish: bool
    message: str | None = None
    requires_user_input: bool = False
    user_prompt: str | None = None  # For INFO action


class DeviceExecutor(Protocol):
    """Protocol for device execution backends."""

    def tap(self, x: int, y: int) -> bool: ...
    def double_tap(self, x: int, y: int) -> bool: ...
    def long_press(self, x: int, y: int, duration_ms: int) -> bool: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> bool: ...
    def type_text(self, text: str) -> bool: ...
    def press_back(self) -> bool: ...
    def press_home(self) -> bool: ...
    def launch_app(self, app_name: str) -> bool: ...
    def get_screen_size(self) -> tuple[int, int]: ...


class ADBExecutor:
    """ADB-based device executor."""

    def __init__(self, device_id: str | None = None, logger: Callable[[str], None] | None = None):
        self.device_id = device_id
        self.logger = logger
        self._adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    def _run_command(self, cmd: str, timeout: int = 30) -> tuple[bool, str]:
        """Run ADB command and return (success, output)."""
        if self.logger:
            self.logger(f"[CMD] {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)


# ... (methods tap, double_tap, etc remain unchanged, but they are inside the class)

    def tap(self, x: int, y: int) -> bool:
        cmd = f"{self._adb_prefix} shell input tap {x} {y}"
        success, _ = self._run_command(cmd)
        return success

    def double_tap(self, x: int, y: int) -> bool:
        cmd = f"{self._adb_prefix} shell input tap {x} {y} && {self._adb_prefix} shell input tap {x} {y}"
        success, _ = self._run_command(cmd)
        return success

    def long_press(self, x: int, y: int, duration_ms: int = 2000) -> bool:
        # Use swipe with same start/end for long press
        cmd = f"{self._adb_prefix} shell input swipe {x} {y} {x} {y} {duration_ms}"
        success, _ = self._run_command(cmd)
        return success

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> bool:
        cmd = f"{self._adb_prefix} shell input swipe {x1} {y1} {x2} {y2} {duration_ms}"
        success, _ = self._run_command(cmd)
        return success

    def type_text(self, text: str) -> bool:
        # Escape special characters
        escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace(" ", "\\ ")
        # Try YADB first (supports Chinese), fallback to input text
        yadb_cmd = f"{self._adb_prefix} shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard '{escaped}'"
        success, _ = self._run_command(yadb_cmd)
        if not success:
            # Fallback to adb input (ASCII only)
            cmd = f"{self._adb_prefix} shell input text '{escaped}'"
            success, _ = self._run_command(cmd)
        return success

    def press_back(self) -> bool:
        cmd = f"{self._adb_prefix} shell input keyevent 4"
        success, _ = self._run_command(cmd)
        return success

    def press_home(self) -> bool:
        cmd = f"{self._adb_prefix} shell input keyevent 3"
        success, _ = self._run_command(cmd)
        return success

    def launch_app(self, app_name: str) -> bool:
        # Try to find package name and launch
        from ..device.apps import find_package_name
        package = find_package_name(app_name)
        if not package:
            return False

        cmd = f"{self._adb_prefix} shell monkey -p {package} -c android.intent.category.LAUNCHER 1"
        success, _ = self._run_command(cmd)
        return success

    def get_screen_size(self) -> tuple[int, int]:
        cmd = f"{self._adb_prefix} shell wm size"
        success, output = self._run_command(cmd)
        if success and "Physical size:" in output:
            size_str = output.split("Physical size:")[-1].strip()
            w, h = size_str.split("x")
            return int(w), int(h)
        return 1080, 1920  # Default fallback


class MCPExecutor:
    """MCP-based device executor (uses android-phone MCP tools)."""

    def __init__(self, mcp_client: Any = None):
        self.mcp_client = mcp_client
        self._screen_size: tuple[int, int] | None = None

    def _call_mcp(self, tool_name: str, **params) -> dict:
        """Call MCP tool."""
        if self.mcp_client is None:
            raise RuntimeError("MCP client not initialized")
        return self.mcp_client.call_tool(f"mcp__android-phone__{tool_name}", params)

    def tap(self, x: int, y: int) -> bool:
        try:
            self._call_mcp("phone_tap", x=x, y=y)
            return True
        except Exception:
            return False

    def double_tap(self, x: int, y: int) -> bool:
        try:
            self._call_mcp("phone_double_tap", x=x, y=y)
            return True
        except Exception:
            return False

    def long_press(self, x: int, y: int, duration_ms: int = 2000) -> bool:
        try:
            self._call_mcp("phone_long_press", x=x, y=y, duration_ms=duration_ms)
            return True
        except Exception:
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> bool:
        try:
            self._call_mcp("phone_swipe", start_x=x1, start_y=y1, end_x=x2, end_y=y2, duration_ms=duration_ms)
            return True
        except Exception:
            return False

    def type_text(self, text: str) -> bool:
        try:
            self._call_mcp("phone_type", text=text)
            return True
        except Exception:
            return False

    def press_back(self) -> bool:
        try:
            self._call_mcp("phone_back")
            return True
        except Exception:
            return False

    def press_home(self) -> bool:
        try:
            self._call_mcp("phone_home")
            return True
        except Exception:
            return False

    def launch_app(self, app_name: str) -> bool:
        try:
            self._call_mcp("phone_launch_app", app_name=app_name)
            return True
        except Exception:
            return False

    def get_screen_size(self) -> tuple[int, int]:
        if self._screen_size:
            return self._screen_size
        try:
            result = self._call_mcp("phone_device_info")
            # Parse screen size from result
            self._screen_size = (1080, 1920)  # Default
            return self._screen_size
        except Exception:
            return 1080, 1920


class ActionHandler:
    """
    Executes actions on Android device.

    Supports:
    - Callback for sensitive operation confirmation
    - Callback for human takeover requests
    - Multiple execution backends (ADB, MCP)
    """

    # Default swipe distance as fraction of screen
    DEFAULT_SWIPE_FRACTION = 0.3
    DEFAULT_SWIPE_DURATION_MS = 500
    DEFAULT_LONG_PRESS_MS = 2000

    def __init__(
        self,
        executor: DeviceExecutor | None = None,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        info_callback: Callable[[str], str] | None = None,
        logger: Callable[[str], None] | None = None,
    ):
        """
        Initialize action handler.

        Args:
            executor: Device executor instance (ADB or MCP)
            device_id: ADB device ID (used if executor not provided)
            confirmation_callback: Called for sensitive operations, returns True to proceed
            takeover_callback: Called when agent requests human takeover
            info_callback: Called when agent needs information from user
            logger: Callback for logging execution details
        """
        self.executor = executor or ADBExecutor(device_id, logger=logger)
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover
        self.info_callback = info_callback or self._default_info

        self._screen_size: tuple[int, int] | None = None

    @property
    def screen_size(self) -> tuple[int, int]:
        """Get screen size, caching the result."""
        if self._screen_size is None:
            self._screen_size = self.executor.get_screen_size()
        return self._screen_size

    def execute(self, action: Action) -> ActionResult:
        """
        Execute an action.

        Args:
            action: Action to execute

        Returns:
            ActionResult with execution status
        """
        action_type = action.action_type
        params = action.params

        # Control flow actions
        if action_type == ActionType.COMPLETE:
            return ActionResult(
                success=True,
                should_finish=True,
                message=params.get("return", "Task completed")
            )

        if action_type == ActionType.ABORT:
            return ActionResult(
                success=True,
                should_finish=True,
                message=params.get("value", params.get("reason", "Task aborted"))
            )

        if action_type == ActionType.INFO:
            return ActionResult(
                success=True,
                should_finish=False,
                requires_user_input=True,
                user_prompt=params.get("value", "Please provide more information")
            )

        if action_type == ActionType.TAKE_OVER:
            message = params.get("message", "Human intervention required")
            self.takeover_callback(message)
            return ActionResult(success=True, should_finish=False)

        # Get handler method
        handler = self._get_handler(action_type)
        if handler is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action type: {action_type.value}"
            )

        try:
            return handler(action)
        except Exception as e:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Action failed: {e}"
            )

    def _get_handler(self, action_type: ActionType) -> Callable[[Action], ActionResult] | None:
        """Get handler method for action type."""
        handlers = {
            ActionType.CLICK: self._handle_click,
            ActionType.DOUBLE_TAP: self._handle_double_tap,
            ActionType.LONG_PRESS: self._handle_long_press,
            ActionType.SWIPE: self._handle_swipe,
            ActionType.TYPE: self._handle_type,
            ActionType.BACK: self._handle_back,
            ActionType.HOME: self._handle_home,
            ActionType.LAUNCH: self._handle_launch,
            ActionType.WAIT: self._handle_wait,
            ActionType.NOTE: self._handle_note,
        }
        return handlers.get(action_type)

    def _to_absolute(self, point: list[int] | tuple[int, int]) -> tuple[int, int]:
        """Convert normalized coordinates to absolute pixels."""
        width, height = self.screen_size
        return (
            int(point[0] * width / 1000),
            int(point[1] * height / 1000)
        )

    def _handle_click(self, action: Action) -> ActionResult:
        point = action.params.get("point")
        if not point:
            return ActionResult(False, False, "Missing point parameter")

        # Check for sensitive operation
        if "message" in action.params:
            if not self.confirmation_callback(action.params["message"]):
                return ActionResult(False, True, "User cancelled sensitive operation")

        x, y = self._to_absolute(point)
        success = self.executor.tap(x, y)
        return ActionResult(success, False)

    def _handle_double_tap(self, action: Action) -> ActionResult:
        point = action.params.get("point")
        if not point:
            return ActionResult(False, False, "Missing point parameter")

        x, y = self._to_absolute(point)
        success = self.executor.double_tap(x, y)
        return ActionResult(success, False)

    def _handle_long_press(self, action: Action) -> ActionResult:
        point = action.params.get("point")
        if not point:
            return ActionResult(False, False, "Missing point parameter")

        duration_ms = int(float(action.params.get("duration", 2)) * 1000)
        x, y = self._to_absolute(point)
        success = self.executor.long_press(x, y, duration_ms)
        return ActionResult(success, False)

    def _handle_swipe(self, action: Action) -> ActionResult:
        params = action.params

        # Two-point swipe
        if "point1" in params and "point2" in params:
            x1, y1 = self._to_absolute(params["point1"])
            x2, y2 = self._to_absolute(params["point2"])
        # Point + direction swipe
        elif "point" in params and "direction" in params:
            x, y = self._to_absolute(params["point"])
            direction = params["direction"].upper()
            width, height = self.screen_size
            delta_x = int(self.DEFAULT_SWIPE_FRACTION * width)
            delta_y = int(self.DEFAULT_SWIPE_FRACTION * height)

            direction_map = {
                "UP": (x, y, x, y - delta_y),
                "DOWN": (x, y, x, y + delta_y),
                "LEFT": (x, y, x - delta_x, y),
                "RIGHT": (x, y, x + delta_x, y),
            }

            if direction not in direction_map:
                return ActionResult(False, False, f"Invalid direction: {direction}")

            x1, y1, x2, y2 = direction_map[direction]
        else:
            return ActionResult(False, False, "Missing swipe parameters")

        duration_ms = int(float(params.get("duration", 0.5)) * 1000)
        success = self.executor.swipe(x1, y1, x2, y2, duration_ms)
        return ActionResult(success, False)

    def _handle_type(self, action: Action) -> ActionResult:
        text = action.params.get("value", "")

        # Tap on input field first if point provided
        if "point" in action.params:
            x, y = self._to_absolute(action.params["point"])
            self.executor.tap(x, y)
            time.sleep(0.5)

        success = self.executor.type_text(text)
        return ActionResult(success, False)

    def _handle_back(self, action: Action) -> ActionResult:
        success = self.executor.press_back()
        return ActionResult(success, False)

    def _handle_home(self, action: Action) -> ActionResult:
        success = self.executor.press_home()
        return ActionResult(success, False)

    def _handle_launch(self, action: Action) -> ActionResult:
        app_name = action.params.get("value")
        if not app_name:
            return ActionResult(False, False, "Missing app name")

        success = self.executor.launch_app(app_name)
        if not success:
            return ActionResult(False, False, f"Failed to launch app: {app_name}")
        return ActionResult(True, False)

    def _handle_wait(self, action: Action) -> ActionResult:
        try:
            duration = float(action.params.get("value", 1))
        except (ValueError, TypeError):
            duration = 1.0

        time.sleep(duration)
        return ActionResult(True, False)

    def _handle_note(self, action: Action) -> ActionResult:
        # Note action is for internal recording, no device action needed
        return ActionResult(True, False)

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """Default confirmation using console input."""
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """Default takeover using console input."""
        input(f"{message}\nPress Enter after completing manual operation...")

    @staticmethod
    def _default_info(prompt: str) -> str:
        """Default info callback using console input."""
        return input(f"Agent asks: {prompt}\nYour response: ")
