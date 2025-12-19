"""
Action Parser - Parse LLM output to structured actions.

Supports multiple formats:
1. Tab-separated format (gelab-zero style):
   <THINK>...</THINK>
   explain:xxx  action:CLICK  point:x,y  summary:xxx

2. Function call format (AutoGLM style):
   do(action="Tap", element=[x, y])
   finish(message="...")
"""

import re
import ast
from typing import Any
from collections import OrderedDict

from .space import Action, ActionType


class ActionParser:
    """Parser for converting LLM output to structured actions."""

    # Map from various action names to standardized ActionType
    ACTION_NAME_MAP: dict[str, ActionType] = {
        # Standard names
        "CLICK": ActionType.CLICK,
        "DOUBLE_TAP": ActionType.DOUBLE_TAP,
        "DOUBLE_CLICK": ActionType.DOUBLE_TAP,
        "LONG_PRESS": ActionType.LONG_PRESS,
        "LONGPRESS": ActionType.LONG_PRESS,
        "SWIPE": ActionType.SWIPE,
        "SLIDE": ActionType.SWIPE,
        "SCROLL": ActionType.SWIPE,
        "TYPE": ActionType.TYPE,
        "BACK": ActionType.BACK,
        "HOME": ActionType.HOME,
        "LAUNCH": ActionType.LAUNCH,
        "AWAKE": ActionType.LAUNCH,
        "WAIT": ActionType.WAIT,
        "INFO": ActionType.INFO,
        "COMPLETE": ActionType.COMPLETE,
        "ABORT": ActionType.ABORT,
        "TAKE_OVER": ActionType.TAKE_OVER,
        "Take_over": ActionType.TAKE_OVER,
        "NOTE": ActionType.NOTE,
        # AutoGLM style names
        "Tap": ActionType.CLICK,
        "Double Tap": ActionType.DOUBLE_TAP,
        "Long Press": ActionType.LONG_PRESS,
        "Swipe": ActionType.SWIPE,
        "Type": ActionType.TYPE,
        "Type_Name": ActionType.TYPE,
        "Back": ActionType.BACK,
        "Home": ActionType.HOME,
        "Launch": ActionType.LAUNCH,
        "Wait": ActionType.WAIT,
        "Interact": ActionType.INFO,
        "Call_API": ActionType.NOTE,
    }

    @classmethod
    def parse(cls, response: str) -> Action:
        """
        Parse LLM response to Action.

        Auto-detects format and delegates to appropriate parser.
        """
        response = response.strip()

        # Try AutoGLM function call format (scan for keywords)
        if "finish(message=" in response:
            parts = response.split("finish(message=", 1)
            thinking = parts[0].strip()
            # Extract clean function call
            full_call = cls._extract_balanced_call(response, "finish(message=")
            if full_call:
                action = cls._parse_function_call(full_call)
                if thinking:
                    action.thinking = thinking
                return action

        if "do(action=" in response:
            parts = response.split("do(action=", 1)
            thinking = parts[0].strip()
            # Extract clean function call
            full_call = cls._extract_balanced_call(response, "do(action=")
            if full_call:
                action = cls._parse_function_call(full_call)
                if thinking:
                    action.thinking = thinking
                return action

        # Default to tab-separated format
        return cls._parse_tab_format(response)

    @staticmethod
    def _extract_balanced_call(text: str, start_marker: str) -> str | None:
        """Extract balanced function call starting with marker."""
        start = text.find(start_marker)
        if start == -1:
            return None
        
        count = 0
        in_string = False
        string_char = None
        escape = False
        
        for i, char in enumerate(text[start:], start):
            if in_string:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == string_char:
                    in_string = False
            else:
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                elif char == '(':
                    count += 1
                elif char == ')':
                    count -= 1
                    if count == 0:
                        return text[start:i+1]
        return None  # Malformed or incomplete

    @classmethod
    def _parse_tab_format(cls, response: str) -> Action:
        """
        Parse tab-separated format:
        <THINK>...</THINK>
        explain:xxx  action:CLICK  point:x,y  summary:xxx
        """
        # Normalize THINK tags
        response = cls._normalize_think_tags(response)

        # Extract thinking and key-value parts
        thinking = ""
        kv_part = response

        if "<THINK>" in response and "</THINK>" in response:
            try:
                thinking = response.split("<THINK>")[1].split("</THINK>")[0].strip()
                kv_part = response.split("</THINK>")[1].strip()
            except IndexError:
                pass

        # Parse key-value pairs
        data = OrderedDict()
        data["thinking"] = thinking

        # Split by tab, handling both tab and multiple spaces
        kvs = re.split(r'\t+|\s{2,}', kv_part)
        kvs = [kv.strip() for kv in kvs if kv.strip()]

        for kv in kvs:
            if ":" not in kv:
                continue

            key, value = kv.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "action":
                data["action_type"] = cls._normalize_action_type(value)
            elif key == "explain":
                data["explanation"] = value
            elif key == "summary":
                data["summary"] = value
            elif key in ("point", "point1", "point2"):
                data[key] = cls._parse_point(value)
            elif key == "direction":
                data["direction"] = value.upper()
            elif key == "value":
                data["value"] = value
            elif key == "return":
                data["return"] = value
            else:
                data[key] = value

        return cls._build_action(data)

    @classmethod
    def _parse_function_call(cls, response: str) -> Action:
        """
        Parse AutoGLM function call format:
        do(action="Tap", element=[x, y])
        finish(message="...")
        
        Note: response is expected to be a clean function call string.
        """
        response = response.strip()

        if response.startswith("finish("):
            # Handle finish action
            message = ""
            match = re.search(r'message\s*=\s*["\'](.+?)["\']', response)
            if match:
                message = match.group(1)
            return Action(
                action_type=ActionType.COMPLETE,
                params={"return": message}
            )

        # Handle Type action specially (may contain special characters in text)
        if 'action="Type"' in response or 'action="Type_Name"' in response:
            text_match = re.search(r'text\s*=\s*["\'](.+?)["\'](?:\s*\))?$', response)
            if text_match:
                text = text_match.group(1)
                return Action(
                    action_type=ActionType.TYPE,
                    params={"value": text}
                )

        # Use AST for safe parsing
        try:
            tree = ast.parse(response, mode="eval")
            if not isinstance(tree.body, ast.Call):
                raise ValueError("Expected function call")

            call = tree.body
            data = {}

            for keyword in call.keywords:
                key = keyword.arg
                value = ast.literal_eval(keyword.value)

                if key == "action":
                    data["action_type"] = cls._normalize_action_type(value)
                elif key == "element":
                    data["point"] = value
                elif key == "start":
                    data["point1"] = value
                elif key == "end":
                    data["point2"] = value
                elif key == "text":
                    data["value"] = value
                elif key == "app":
                    data["value"] = value
                elif key == "duration":
                    data["value"] = value
                elif key == "message":
                    if "action_type" not in data:
                        data["action_type"] = ActionType.COMPLETE
                    data["return"] = value
                else:
                    data[key] = value

            return cls._build_action(data)

        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Failed to parse function call: {e}")

    @classmethod
    def _normalize_think_tags(cls, text: str) -> str:
        """Normalize various THINK tag formats."""
        # Fix common typos and case variations
        text = text.replace("<TINK>", "<THINK>").replace("</TINK>", "</THINK>")
        text = text.replace("<think>", "<THINK>").replace("</think>", "</THINK>")
        # Fix spacing issues
        text = re.sub(r"<\s*/?THINK\s*>", lambda m: "<THINK>" if "/" not in m.group() else "</THINK>", text, flags=re.IGNORECASE)
        return text

    @classmethod
    def _normalize_action_type(cls, action_name: str) -> ActionType:
        """Convert action name string to ActionType enum."""
        action_name = action_name.strip()

        # Direct lookup
        if action_name in cls.ACTION_NAME_MAP:
            return cls.ACTION_NAME_MAP[action_name]

        # Case-insensitive lookup
        upper_name = action_name.upper()
        for key, value in cls.ACTION_NAME_MAP.items():
            if key.upper() == upper_name:
                return value

        # Try to match ActionType directly
        try:
            return ActionType(upper_name)
        except ValueError:
            raise ValueError(f"Unknown action type: {action_name}")

    @classmethod
    def _parse_point(cls, value: str) -> list[int]:
        """Parse point from string 'x,y' or 'x y'."""
        coords = value.replace(",", " ").split()
        if len(coords) < 2:
            raise ValueError(f"Invalid point format: {value}")
        return [int(coords[0]), int(coords[1])]

    @classmethod
    def _build_action(cls, data: dict[str, Any]) -> Action:
        """Build Action object from parsed data."""
        action_type = data.pop("action_type", ActionType.COMPLETE)
        thinking = data.pop("thinking", data.pop("cot", ""))
        explanation = data.pop("explanation", data.pop("explain", ""))
        summary = data.pop("summary", "")

        return Action(
            action_type=action_type,
            thinking=thinking,
            explanation=explanation,
            summary=summary,
            params=data
        )

    @classmethod
    def to_string(cls, action: Action, format: str = "tab") -> str:
        """
        Convert Action to string format.

        Args:
            action: Action object
            format: "tab" for tab-separated, "function" for function call

        Returns:
            Formatted action string
        """
        if format == "function":
            return cls._to_function_string(action)
        return cls._to_tab_string(action)

    @classmethod
    def _to_tab_string(cls, action: Action) -> str:
        """Convert to tab-separated format."""
        parts = []

        if action.thinking:
            parts.append(f"<THINK>{action.thinking}</THINK>")

        kv_parts = []
        if action.explanation:
            kv_parts.append(f"explain:{action.explanation}")

        kv_parts.append(f"action:{action.action_type.value}")

        # Add params
        for key, value in action.params.items():
            if isinstance(value, list):
                value = ",".join(str(v) for v in value)
            kv_parts.append(f"{key}:{value}")

        if action.summary:
            kv_parts.append(f"summary:{action.summary}")

        parts.append("\t".join(kv_parts))
        return "\n".join(parts)

    @classmethod
    def _to_function_string(cls, action: Action) -> str:
        """Convert to function call format."""
        params = action.params.copy()

        # Map action type back
        action_name_map = {
            ActionType.CLICK: "Tap",
            ActionType.DOUBLE_TAP: "Double Tap",
            ActionType.LONG_PRESS: "Long Press",
            ActionType.SWIPE: "Swipe",
            ActionType.TYPE: "Type",
            ActionType.BACK: "Back",
            ActionType.HOME: "Home",
            ActionType.LAUNCH: "Launch",
            ActionType.WAIT: "Wait",
            ActionType.INFO: "Interact",
            ActionType.COMPLETE: None,  # Special case
            ActionType.ABORT: None,
        }

        if action.action_type == ActionType.COMPLETE:
            msg = params.get("return", "Task completed")
            return f'finish(message="{msg}")'

        action_name = action_name_map.get(action.action_type, action.action_type.value)

        # Build parameter string
        param_parts = [f'action="{action_name}"']

        if "point" in params:
            param_parts.append(f'element={params["point"]}')
        if "point1" in params:
            param_parts.append(f'start={params["point1"]}')
        if "point2" in params:
            param_parts.append(f'end={params["point2"]}')
        if "value" in params:
            if action.action_type == ActionType.TYPE:
                param_parts.append(f'text="{params["value"]}"')
            elif action.action_type == ActionType.LAUNCH:
                param_parts.append(f'app="{params["value"]}"')
            else:
                param_parts.append(f'value="{params["value"]}"')

        return f'do({", ".join(param_parts)})'
