"""
History Manager - Manage conversation history with robust context and loop detection.

Key features:
- Generates multi-turn chat messages for LLM context (User -> Assistant -> User...)
- Detects and prevents action loops
- Handles image optimization (strips old screenshots)
- Supports task planning integration
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from collections import Counter

from .actions import Action, ActionType
from .planner import TaskPlan, TaskPlanner, TaskStatus, analyze_task_complexity


@dataclass
class HistoryEntry:
    """Single history entry."""
    step: int
    action: Action
    observation: str  # The screen info/text user saw
    screenshot_base64: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_reply: str | None = None  # Reply to INFO action
    sub_task_id: int | None = None  # Which sub-task this step belongs to


@dataclass
class ConversationHistory:
    """Full conversation history."""

    task: str
    entries: list[HistoryEntry] = field(default_factory=list)
    qa_history: list[tuple[str, str]] = field(default_factory=list)  # (question, answer) pairs
    task_plan: TaskPlan | None = None  # Task decomposition plan

    @property
    def step_count(self) -> int:
        """Get current step count."""
        return len(self.entries)

    def add_entry(
        self,
        action: Action,
        observation: str,
        screenshot_base64: str | None = None,
        user_reply: str | None = None
    ) -> None:
        """Add new history entry."""
        sub_task_id = None
        if self.task_plan and self.task_plan.current_sub_task:
            sub_task_id = self.task_plan.current_sub_task.id
        
        entry = HistoryEntry(
            step=self.step_count + 1,
            action=action,
            observation=observation,
            screenshot_base64=screenshot_base64,
            user_reply=user_reply,
            sub_task_id=sub_task_id
        )
        self.entries.append(entry)

        # Track Q&A history
        if action.action_type == ActionType.INFO and user_reply:
            question = action.params.get("value", "")
            self.qa_history.append((question, user_reply))

    def get_recent_actions(self, n: int = 5) -> list[Action]:
        """Get last n actions."""
        return [e.action for e in self.entries[-n:]]

    def to_messages(self, max_history: int = 10) -> list[dict[str, Any]]:
        """
        Convert history to list of messages for LLM.
        
        Structure:
        User: Task + (Summary if truncated)
        User: Step 1 Observation (Image removed)
        Assistant: Step 1 Action
        ...
        User: Step N Observation (Image removed)
        Assistant: Step N Action
        """
        from .llm import MessageBuilder

        messages = []
        
        # Determine start index for history
        start_idx = max(0, len(self.entries) - max_history)
        
        for i, entry in enumerate(self.entries[start_idx:]):
            # User Message (Observation)
            content = entry.observation
            if i == 0 and start_idx > 0:
                content = f"Task: {self.task}\n\n[Previous steps truncated...]\n\n{content}"
            elif i == 0:
                content = f"Task: {self.task}\n\n{content}"

            messages.append(MessageBuilder.create_user_message(
                text=content,
                image_base64=None  # Old history has no image
            ))

            # Assistant Message (Action)
            assistant_content = ""
            if entry.action.thinking:
                assistant_content += f"<think>{entry.action.thinking}</think>\n"
            
            # Minimal action representation
            action_dict = entry.action.to_dict()
            if "thinking" in action_dict:
                del action_dict["thinking"]
            
            import json
            action_json = json.dumps(action_dict, ensure_ascii=False)
            assistant_content += f"```json\n{action_json}\n```"
            
            messages.append(MessageBuilder.create_assistant_message(assistant_content))

            # Add user reply if this step had one (After the action)
            if entry.user_reply:
                messages.append(MessageBuilder.create_user_message(
                    text=f"User Reply: {entry.user_reply}"
                ))
            
        return messages


class LoopDetector:
    """Detects and prevents repetitive action loops."""
    
    def __init__(
        self,
        max_consecutive_same: int = 3,
        max_consecutive_swipes: int = 5,
        max_click_same_point: int = 3,
        point_tolerance: int = 50  # Tolerance for "same" point (in 0-1000 coords)
    ):
        self.max_consecutive_same = max_consecutive_same
        self.max_consecutive_swipes = max_consecutive_swipes
        self.max_click_same_point = max_click_same_point
        self.point_tolerance = point_tolerance
    
    def check_loop(self, entries: list[HistoryEntry]) -> tuple[bool, str]:
        """
        Check if we're in a loop pattern.
        
        Returns:
            Tuple of (is_looping, warning_message)
        """
        if len(entries) < 2:
            return False, ""
        
        # Check 1: Consecutive same action type
        recent = entries[-self.max_consecutive_same:]
        if len(recent) >= self.max_consecutive_same:
            action_types = [e.action.action_type for e in recent]
            if len(set(action_types)) == 1:
                # All same action type
                if action_types[0] == ActionType.SWIPE:
                    if len(entries) >= self.max_consecutive_swipes:
                        swipe_count = sum(
                            1 for e in entries[-self.max_consecutive_swipes:]
                            if e.action.action_type == ActionType.SWIPE
                        )
                        if swipe_count >= self.max_consecutive_swipes:
                            return True, f"连续滑动 {swipe_count} 次，请尝试其他方法（如搜索、返回）"
                elif action_types[0] == ActionType.CLICK:
                    # Check if clicking same point
                    points = [e.action.params.get("point") for e in recent if e.action.params.get("point")]
                    if len(points) >= self.max_click_same_point and self._are_points_similar(points):
                        return True, "多次点击同一位置无效，UI 可能没有响应，请尝试不同位置或操作"
        
        # Check 2: Alternating pattern (A-B-A-B loop)
        if len(entries) >= 4:
            last_four = [e.action.action_type for e in entries[-4:]]
            if last_four[0] == last_four[2] and last_four[1] == last_four[3] and last_four[0] != last_four[1]:
                return True, f"检测到 {last_four[0].value}-{last_four[1].value} 交替循环，请换一种方法"
        
        # Check 3: Exact same action repeated (including params)
        if len(entries) >= 2:
            last_action = entries[-1].action
            prev_action = entries[-2].action
            if self._actions_identical(last_action, prev_action):
                # Check how many times this exact action was repeated
                repeat_count = 1
                for i in range(len(entries) - 2, -1, -1):
                    if self._actions_identical(entries[i].action, last_action):
                        repeat_count += 1
                    else:
                        break
                if repeat_count >= self.max_consecutive_same:
                    return True, f"完全相同的操作重复了 {repeat_count} 次，请尝试其他方法"
        
        return False, ""
    
    def _are_points_similar(self, points: list) -> bool:
        """Check if all points are within tolerance of each other."""
        if not points:
            return False
        
        base = points[0]
        if not isinstance(base, (list, tuple)) or len(base) < 2:
            return False
            
        for point in points[1:]:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                return False
            if abs(point[0] - base[0]) > self.point_tolerance or abs(point[1] - base[1]) > self.point_tolerance:
                return False
        return True
    
    def _actions_identical(self, a1: Action, a2: Action) -> bool:
        """Check if two actions are functionally identical."""
        if a1.action_type != a2.action_type:
            return False
        
        # Compare key params based on action type
        if a1.action_type == ActionType.CLICK:
            p1 = a1.params.get("point")
            p2 = a2.params.get("point")
            if p1 and p2:
                return (abs(p1[0] - p2[0]) <= self.point_tolerance and 
                        abs(p1[1] - p2[1]) <= self.point_tolerance)
        elif a1.action_type == ActionType.TYPE:
            return a1.params.get("value") == a2.params.get("value")
        elif a1.action_type == ActionType.SWIPE:
            p1_start = a1.params.get("point1")
            p1_end = a1.params.get("point2")
            p2_start = a2.params.get("point1")
            p2_end = a2.params.get("point2")
            if p1_start and p1_end and p2_start and p2_end:
                return (self._are_points_similar([p1_start, p2_start]) and
                        self._are_points_similar([p1_end, p2_end]))
        elif a1.action_type in (ActionType.BACK, ActionType.HOME, ActionType.WAIT):
            return True  # These are always "same"
        
        return a1.params == a2.params


class HistoryManager:
    """
    Manages conversation history with robust context handling and loop detection.
    
    Includes:
    - Chat-based history for multi-turn context
    - Loop detection and prevention
    - Task planning integration
    - Efficient context compression
    """

    def __init__(
        self,
        max_history_steps: int = 8,  # Reduced for efficiency
        use_task_planning: bool = True
    ):
        """
        Initialize history manager.

        Args:
            max_history_steps: Max number of past steps to include in context
            use_task_planning: Whether to use task planning for complex tasks
        """
        self.max_history_steps = max_history_steps
        self.use_task_planning = use_task_planning
        self._history: ConversationHistory | None = None
        self.loop_detector = LoopDetector()

    def start_task(self, task: str, llm_client: Any = None) -> TaskPlan | None:
        """
        Start tracking a new task.
        
        Returns:
            TaskPlan if planning was used, None otherwise
        """
        self._history = ConversationHistory(task=task)
        
        # Analyze task complexity and create plan if needed
        if self.use_task_planning:
            complexity = analyze_task_complexity(task)
            if complexity["is_complex"]:
                # Use LLM for complex tasks if available
                plan = TaskPlanner.create_plan(
                    task, 
                    use_llm=(llm_client is not None),
                    llm_client=llm_client
                )
                self._history.task_plan = plan
                # Mark first task as in progress
                if plan.sub_tasks:
                    plan.sub_tasks[0].status = TaskStatus.IN_PROGRESS
                return plan
        
        return None

    def add_action(
        self,
        action: Action,
        observation: str,
        screenshot_base64: str | None = None,
        user_reply: str | None = None
    ) -> None:
        """Record an action."""
        if self._history is None:
            raise RuntimeError("No task started. Call start_task() first.")
        self._history.add_entry(action, observation, screenshot_base64, user_reply)
    
    def advance_sub_task(self) -> bool:
        """
        Mark current sub-task as complete and move to next.
        
        Returns:
            True if there are more sub-tasks, False if all done
        """
        if self._history and self._history.task_plan:
            self._history.task_plan.mark_current_complete()
            # Mark next as in progress
            if self._history.task_plan.current_sub_task:
                self._history.task_plan.current_sub_task.status = TaskStatus.IN_PROGRESS
                return True
            return False
        return True  # No plan, assume not complete

    def check_loop(self) -> tuple[bool, str]:
        """Check if we're stuck in a loop."""
        if self._history is None or not self._history.entries:
            return False, ""
        return self.loop_detector.check_loop(self._history.entries)

    def get_summary(self) -> str:
        """Get text summary of recent actions (backward compatibility/logging)."""
        if self._history is None or not self._history.entries:
            return ""
        
        lines = []
        for entry in self._history.entries[-5:]:
            lines.append(f"Step {entry.step}: {entry.action.action_type.value}")
        return "\n".join(lines)

    def get_recent_actions(self, n: int = 5) -> list[Action]:
        """Get recent actions."""
        if self._history is None:
            return []
        return self._history.get_recent_actions(n)
    
    def get_last_action(self) -> Action | None:
        """Get the very last action."""
        actions = self.get_recent_actions(1)
        return actions[0] if actions else None

    def get_action_summary_for_prompt(self, lang: str = "zh") -> str:
        """Generate a summary of recent actions for inclusion in the prompt."""
        if self._history is None or not self._history.entries:
            return ""
        
        recent = self._history.entries[-self.max_history_steps:]
        
        if lang == "zh":
            lines = ["### 已执行的操作："]
            for entry in recent:
                action = entry.action
                action_str = f"步骤 {entry.step}: {action.action_type.value}"
                if action.params:
                    if "point" in action.params:
                        action_str += f" @ {action.params['point']}"
                    if "value" in action.params:
                        val = str(action.params['value'])[:30]
                        action_str += f" [{val}]"
                lines.append(action_str)
            
            # Add loop warning if detected
            is_loop, loop_msg = self.check_loop()
            if is_loop:
                lines.append(f"\n⚠️ **警告**：{loop_msg}")
        else:
            lines = ["### Executed Actions:"]
            for entry in recent:
                action = entry.action
                action_str = f"Step {entry.step}: {action.action_type.value}"
                if action.params:
                    if "point" in action.params:
                        action_str += f" @ {action.params['point']}"
                    if "value" in action.params:
                        val = str(action.params['value'])[:30]
                        action_str += f" [{val}]"
                lines.append(action_str)
            
            is_loop, loop_msg = self.check_loop()
            if is_loop:
                lines.append(f"\n⚠️ **Warning**: {loop_msg}")
        
        return "\n".join(lines)

    @property
    def step_count(self) -> int:
        """Get current step count."""
        if self._history is None:
            return 0
        return self._history.step_count
        
    @property
    def task(self) -> str | None:
        """Get current task."""
        if self._history is None:
            return None
        return self._history.task
    
    @property
    def task_plan(self) -> TaskPlan | None:
        """Get current task plan."""
        if self._history is None:
            return None
        return self._history.task_plan

    def reset(self) -> None:
        """Reset history."""
        self._history = None

    def build_context_messages(
        self,
        system_prompt: str,
        current_screenshot_b64: str,
        current_app: dict[str, str] | None = None,
        lang: str = "zh"
    ) -> list[dict[str, Any]]:
        """
        Build messages for LLM context.
        
        Structure:
        1. System Message
        2. History Messages (User/Assistant chain without images) - limited
        3. Current User Message (Task Plan + History Summary + Observation + Image)
        """
        from .llm import MessageBuilder

        messages = []

        # 1. System Message
        messages.append(MessageBuilder.create_system_message(system_prompt))

        # 2. History Messages - only include recent ones for efficiency
        if self._history and self._history.entries:
            # Only include last few complete turns
            history_msgs = self._history.to_messages(self.max_history_steps)
            messages.extend(history_msgs)

        # 3. Current User Message
        current_text = ""
        
        # 3a. Task and Plan
        if lang == "zh":
            current_text += f"## 用户任务\n{self.task}\n\n"
        else:
            current_text += f"## User Task\n{self.task}\n\n"
        
        # 3b. Task Plan (if available)
        if self._history and self._history.task_plan:
            current_text += self._history.task_plan.to_prompt(lang)
            current_text += "\n\n"
        
        # 3c. Action History Summary
        action_summary = self.get_action_summary_for_prompt(lang)
        if action_summary:
            current_text += f"{action_summary}\n\n"
        
        # 3d. Current Screen Info
        screen_info = ""
        if current_app:
            screen_info = MessageBuilder.build_screen_info(current_app)
        
        if lang == "zh":
            current_text += f"## 当前屏幕状态\n{screen_info}\n\n"
            
            # Add strong reminder about task completion
            if self._history and self._history.task_plan:
                if not self._history.task_plan.is_complete:
                    current_sub = self._history.task_plan.current_sub_task
                    if current_sub:
                        current_text += f"**当前目标**: {current_sub.description}\n"
                    current_text += "**请继续执行任务，只有所有步骤完成后才能使用 finish！**"
            else:
                current_text += "**请分析屏幕并继续执行任务。只有任务完全完成才能使用 finish！**"
        else:
            current_text += f"## Current Screen\n{screen_info}\n\n"
            current_text += "**Analyze the screen and continue. Only use finish when task is FULLY complete!**"

        messages.append(MessageBuilder.create_user_message(
            text=current_text,
            image_base64=current_screenshot_b64
        ))

        return messages
