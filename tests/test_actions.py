"""Tests for action parsing and handling."""

import pytest
from omg_agent.core.agent.actions import ActionParser, ActionType


class TestActionParser:
    """Test action parser."""

    def setup_method(self):
        """Setup test fixtures."""
        self.parser = ActionParser()

    def test_parse_click(self):
        """Test parsing CLICK action."""
        action = self.parser.parse("CLICK(500, 300)")

        assert action is not None
        assert action.action_type == ActionType.CLICK
        assert action.params["x"] == 500
        assert action.params["y"] == 300

    def test_parse_click_with_description(self):
        """Test parsing CLICK with description."""
        action = self.parser.parse('CLICK(500, 300, "点击按钮")')

        assert action is not None
        assert action.action_type == ActionType.CLICK
        assert action.params["x"] == 500
        assert action.params["y"] == 300

    def test_parse_swipe(self):
        """Test parsing SWIPE action."""
        action = self.parser.parse("SWIPE(100, 500, 100, 200)")

        assert action is not None
        assert action.action_type == ActionType.SWIPE
        assert action.params["x1"] == 100
        assert action.params["y1"] == 500
        assert action.params["x2"] == 100
        assert action.params["y2"] == 200

    def test_parse_type(self):
        """Test parsing TYPE action."""
        action = self.parser.parse('TYPE("hello world")')

        assert action is not None
        assert action.action_type == ActionType.TYPE
        assert action.params["text"] == "hello world"

    def test_parse_type_chinese(self):
        """Test parsing TYPE with Chinese text."""
        action = self.parser.parse('TYPE("你好世界")')

        assert action is not None
        assert action.action_type == ActionType.TYPE
        assert action.params["text"] == "你好世界"

    def test_parse_launch(self):
        """Test parsing LAUNCH action."""
        action = self.parser.parse('LAUNCH("微信")')

        assert action is not None
        assert action.action_type == ActionType.LAUNCH
        assert action.params["app"] == "微信"

    def test_parse_back(self):
        """Test parsing BACK action."""
        action = self.parser.parse("BACK()")

        assert action is not None
        assert action.action_type == ActionType.BACK

    def test_parse_home(self):
        """Test parsing HOME action."""
        action = self.parser.parse("HOME()")

        assert action is not None
        assert action.action_type == ActionType.HOME

    def test_parse_wait(self):
        """Test parsing WAIT action."""
        action = self.parser.parse("WAIT(3)")

        assert action is not None
        assert action.action_type == ActionType.WAIT
        assert action.params["seconds"] == 3

    def test_parse_complete(self):
        """Test parsing COMPLETE action."""
        action = self.parser.parse('COMPLETE("任务完成")')

        assert action is not None
        assert action.action_type == ActionType.COMPLETE
        assert action.params["message"] == "任务完成"

    def test_parse_invalid_action(self):
        """Test parsing invalid action returns None."""
        action = self.parser.parse("INVALID_ACTION()")

        assert action is None

    def test_parse_malformed_action(self):
        """Test parsing malformed action returns None."""
        action = self.parser.parse("CLICK(")

        assert action is None

    def test_parse_from_response(self):
        """Test parsing action from LLM response text."""
        response = """
        分析当前屏幕，我需要点击设置按钮。

        CLICK(540, 1200)
        """
        action = self.parser.parse(response)

        assert action is not None
        assert action.action_type == ActionType.CLICK


class TestActionType:
    """Test action type enum."""

    def test_action_types_exist(self):
        """Test all expected action types exist."""
        expected_types = [
            "CLICK",
            "DOUBLE_TAP",
            "LONG_PRESS",
            "SWIPE",
            "TYPE",
            "BACK",
            "HOME",
            "LAUNCH",
            "WAIT",
            "INFO",
            "COMPLETE",
            "ABORT",
            "TAKE_OVER",
        ]

        for action_type in expected_types:
            assert hasattr(ActionType, action_type)
