"""
PhoneAgent - Main agent class for phone automation.

Combines the best features from Open-AutoGLM and gelab-zero:
- Clean architecture with dataclass configs
- Session management for task resumption
- History summary compression
- Multiple reply modes for INFO action
- Callback mechanisms for human intervention
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from enum import Enum

from .actions import ActionHandler, ActionParser, ActionResult, ActionSpace
from .actions.space import Action, ActionType
from .device.screenshot import take_screenshot, get_current_app, is_screen_on, wake_screen
from .history import HistoryManager, HistoryEntry
from .llm import LLMClient, LLMConfig, MessageBuilder
from .prompts import get_system_prompt
from .session import SessionManager

# 配置模块级日志器
logger = logging.getLogger(__name__)


class ReplyMode(str, Enum):
    """How to handle INFO actions."""
    AUTO = "auto"  # Auto-reply using LLM
    MANUAL = "manual"  # Wait for user input
    CALLBACK = "callback"  # Use callback function
    PAUSE = "pause"  # Pause session, return to caller


@dataclass
class AgentConfig:
    """Configuration for PhoneAgent."""

    # Device settings
    device_id: str | None = None

    # Execution limits
    max_steps: int = 100
    step_delay: float = 1.0  # Delay between steps

    # Language
    lang: str = "zh"

    # System prompt (auto-loaded if None)
    system_prompt: str | None = None

    # Reply mode for INFO actions
    reply_mode: ReplyMode = ReplyMode.CALLBACK

    # Session storage
    session_dir: str | None = None

    # Auto wake screen
    auto_wake_screen: bool = True

    # Auto press home before task
    reset_to_home: bool = True
    
    # Verbose output (deprecated, use logging instead)
    verbose: bool = False

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: Action | None
    action_result: ActionResult | None = None
    message: str | None = None

    # For INFO action handling
    needs_user_input: bool = False
    user_prompt: str | None = None

    # Session info
    session_id: str | None = None
    step_count: int = 0

    @property
    def thinking(self) -> str:
        """Get thinking content from action (backward compatibility)."""
        if self.action:
            return self.action.thinking
        return ""


@dataclass
class RunResult:
    """Result of running a complete task."""

    success: bool
    message: str
    step_count: int
    session_id: str | None = None
    final_action: Action | None = None

    # Stop reason
    stop_reason: Literal[
        "completed",
        "aborted",
        "max_steps",
        "error",
        "paused",
        "screen_off"
    ] = "completed"


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Features:
    - Session management for task resumption
    - History summary compression for efficient context
    - Multiple reply modes for user interaction
    - Callback mechanisms for sensitive operations

    Example:
        >>> from omg_agent.core.agent import PhoneAgent, AgentConfig
        >>> from omg_agent.core.agent.llm import LLMConfig
        >>>
        >>> llm_config = LLMConfig(provider="openai", model="gpt-4o")
        >>> agent_config = AgentConfig(device_id="emulator-5554")
        >>> agent = PhoneAgent(llm_config, agent_config)
        >>>
        >>> result = agent.run("Open WeChat and send 'Hello' to John")
        >>> print(result.message)
    """

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        agent_config: AgentConfig | None = None,
        # Callbacks
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        info_callback: Callable[[str], str] | None = None,
        # Progress callback
        on_step: Callable[[StepResult], None] | None = None,
        # Logging callback
        log_callback: Callable[[str], None] | None = None,
        # Screenshot provider (for GUI integration)
        screenshot_provider: Callable[[], Any] | None = None,
        # Backward compatibility aliases
        model_config: LLMConfig | None = None,
        logger: Callable[[str], None] | None = None,  # Alias for log_callback
    ):
        """
        Initialize PhoneAgent.

        Args:
            llm_config: Configuration for LLM client
            agent_config: Agent behavior configuration
            confirmation_callback: Called for sensitive operation confirmation
            takeover_callback: Called when agent requests human takeover
            info_callback: Called when agent needs information from user
            on_step: Called after each step with results
            log_callback: Callback for logging (deprecated)
            screenshot_provider: Optional callable that returns Screenshot object
            model_config: Alias for llm_config (backward compatibility)
        """
        # Handle backward compatibility
        if model_config is not None and llm_config is None:
            llm_config = model_config
        
        # Handle logger alias
        if logger is not None and log_callback is None:
            log_callback = logger

        self.llm_config = llm_config or LLMConfig()
        self.config = agent_config or AgentConfig()
        
        # Log callback (for GUI integration)
        self._log_callback = log_callback

        # [Auto-Detect] Switch Prompt based on Model
        model_name = self.llm_config.model.lower()
        is_default_prompt = self.config.system_prompt is None or "GUI-Agent" in self.config.system_prompt

        if is_default_prompt:
            if any(k in model_name for k in ["autoglm", "glm-4v"]):
                from .prompts.autoglm import get_autoglm_prompt
                self.config.system_prompt = get_autoglm_prompt(self.config.lang)
                self._log(f"🧠 Applied AutoGLM-specific prompt", "debug")
            elif "step" in model_name:
                from .prompts.step import get_step_prompt
                self.config.system_prompt = get_step_prompt(self.config.lang)
                self._log(f"🧠 Applied Step-specific prompt", "debug")

        # Screenshot provider for GUI integration
        self._screenshot_provider = screenshot_provider
        
        # Initialize components

        # Initialize components
        self.llm_client = LLMClient(self.llm_config)
        self.action_handler = ActionHandler(
            device_id=self.config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
            info_callback=info_callback,
            logger=log_callback
        )
        self.history_manager = HistoryManager()
        self.session_manager = SessionManager(self.config.session_dir)

        # Callbacks
        self._on_step = on_step

        # Current session
        self._current_session_id: str | None = None
        
        # Error recovery tracking
        self._parse_error_count: int = 0
        self._max_parse_errors: int = 3  # Max consecutive parse errors before aborting

    def _log(self, message: str, level: str = "info") -> None:
        """Internal logging method."""
        if level == "debug":
            logger.debug(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)
        
        # Also call log callback if provided (for GUI)
        if self._log_callback:
            self._log_callback(message)

    def run(
        self,
        task: str,
        session_id: str | None = None,
        user_reply: str | None = None
    ) -> RunResult:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task
            session_id: Resume existing session (for INFO action handling)
            user_reply: User's reply when resuming paused session

        Returns:
            RunResult with completion status and message
        """
        # Initialize or resume session
        if session_id:
            session = self.session_manager.resume_session(session_id)
            if session is None:
                return RunResult(
                    success=False,
                    message=f"Session not found: {session_id}",
                    step_count=0,
                    stop_reason="error"
                )
            self._current_session_id = session_id
        else:
            # New task
            self._current_session_id = self.session_manager.create_session(
                task=task,
                device_id=self.config.device_id
            )
            
            # Start task with planning (uses LLM for complex tasks)
            task_plan = self.history_manager.start_task(task, llm_client=self.llm_client)
            if task_plan:
                self._log(f"Task Plan: {len(task_plan.sub_tasks)} steps identified")

            # Reset to home if configured
            if self.config.reset_to_home:
                self.action_handler.executor.press_home()
                time.sleep(0.5)

        self._log(f"Session: {self._current_session_id}")
        self._log(f"Task: {task}")

        # Run loop
        last_result = None
        stop_reason: Literal["completed", "aborted", "max_steps", "error", "paused", "screen_off"] = "max_steps"

        for step in range(self.config.max_steps):
            # Check screen status
            if self.config.auto_wake_screen:
                if not is_screen_on(self.config.device_id):
                    wake_screen(self.config.device_id)
                    time.sleep(1)

            if not is_screen_on(self.config.device_id):
                stop_reason = "screen_off"
                break

            # Execute step
            result = self._execute_step(user_reply if step == 0 and user_reply else None)
            last_result = result

            # Update session
            self.session_manager.update_session(
                self._current_session_id,
                step_count=result.step_count,
                history_summary=self.history_manager.get_summary()
            )

            # Callback
            if self._on_step:
                self._on_step(result)

            # Check termination conditions
            if result.finished:
                if result.action and result.action.action_type == ActionType.COMPLETE:
                    stop_reason = "completed"
                    self.session_manager.complete_session(
                        self._current_session_id,
                        result.message
                    )
                elif result.action and result.action.action_type == ActionType.ABORT:
                    stop_reason = "aborted"
                    self.session_manager.abort_session(
                        self._current_session_id,
                        result.message
                    )
                break

            # Handle INFO action
            if result.needs_user_input:
                if self.config.reply_mode == ReplyMode.PAUSE:
                    self.session_manager.pause_session(
                        self._current_session_id,
                        result.user_prompt or ""
                    )
                    stop_reason = "paused"
                    break
                elif self.config.reply_mode == ReplyMode.AUTO:
                    user_reply = self._auto_reply(task, result.user_prompt or "")
                elif self.config.reply_mode == ReplyMode.CALLBACK:
                    user_reply = self.action_handler.info_callback(result.user_prompt or "")
                elif self.config.reply_mode == ReplyMode.MANUAL:
                    user_reply = input(f"Agent asks: {result.user_prompt}\nYour response: ")

                continue

            # Delay between steps
            time.sleep(self.config.step_delay)
            user_reply = None

        # Build result
        return RunResult(
            success=stop_reason == "completed",
            message=last_result.message if last_result else "No steps executed",
            step_count=self.history_manager.step_count,
            session_id=self._current_session_id,
            final_action=last_result.action if last_result else None,
            stop_reason=stop_reason
        )

    def step(self, task: str | None = None, user_reply: str | None = None) -> StepResult:
        """
        Execute a single step.

        Useful for manual control or integration with external systems.

        Args:
            task: Task description (required for first step)
            user_reply: User's reply to previous INFO action

        Returns:
            StepResult with step details
        """
        is_first = self.history_manager.step_count == 0

        if is_first:
            if not task:
                raise ValueError("Task is required for the first step")
            task_plan = self.history_manager.start_task(task, llm_client=self.llm_client)
            if task_plan:
                self._log(f"Task Plan: {len(task_plan.sub_tasks)} steps")

        return self._execute_step(user_reply)

    def _execute_step(self, user_reply: str | None = None) -> StepResult:
        """Execute a single step of the agent loop."""

        step_num = self.history_manager.step_count + 1
        self._log(f"Step {step_num}")

        # Capture current screen state
        try:
            if self._screenshot_provider:
                screenshot = self._screenshot_provider()
                if screenshot is None:
                    screenshot = take_screenshot(self.config.device_id)
            else:
                screenshot = take_screenshot(self.config.device_id)
            current_app = get_current_app(self.config.device_id)
        except Exception as e:
            self._log(f"Failed to capture screen: {e}", "error")
            return StepResult(
                success=False,
                finished=True,
                action=None,
                message=f"Failed to capture screen: {e}",
                step_count=step_num
            )

        # Build screen info for observation
        screen_info = ""
        if current_app:
            screen_info = MessageBuilder.build_screen_info(current_app)
            
        # [Dynamic Plan Update] Analyze screen state and adjust plan
        self._update_plan_from_screen(screen_info)

        # Build context messages
        messages = self.history_manager.build_context_messages(
            system_prompt=self.config.system_prompt,
            current_screenshot_b64=screenshot.base64_data,
            current_app=current_app,
            lang=self.config.lang
        )

        # Add user reply to context if provided
        if user_reply and self.history_manager._history and self.history_manager._history.entries:
             last_entry = self.history_manager._history.entries[-1]
             last_entry.user_reply = user_reply

        # Get LLM response
        try:
            response = self.llm_client.request(messages)
            
            if response.thinking:
                self._log(f"Thinking: {response.thinking[:200]}..." if len(response.thinking) > 200 else f"Thinking: {response.thinking}", "debug")

        except Exception as e:
            self._log(f"LLM error: {e}", "error")
            return StepResult(
                success=False,
                finished=True,
                action=None,
                message=f"LLM error: {e}",
                step_count=step_num
            )

        # Parse action
        try:
            action = ActionParser.parse(response.action or response.content)
            
            if not action.thinking and response.thinking:
                action.thinking = response.thinking
            
            # Reset error count on successful parse
            self._parse_error_count = 0
                
        except ValueError as e:
            self._parse_error_count += 1
            self._log(f"Failed to parse action ({self._parse_error_count}/{self._max_parse_errors}): {e}", "warning")
            self._log(f"Raw response: {(response.action or response.content)[:200]}", "debug")
            
            # Check if we've exceeded max parse errors
            if self._parse_error_count >= self._max_parse_errors:
                self._log(f"❌ Too many parse errors, aborting task", "error")
                return StepResult(
                    success=False,
                    finished=True,
                    action=Action(
                        action_type=ActionType.ABORT,
                        params={"value": f"LLM response parsing failed {self._parse_error_count} times"},
                        thinking="LLM is not returning parseable actions."
                    ),
                    message=f"Task aborted: LLM response parsing failed repeatedly",
                    step_count=step_num
                )
            
            # Use WAIT to give the model another chance
            action = Action(
                action_type=ActionType.WAIT,
                params={"value": "1"},
                thinking=f"Action parsing failed: {e}. Waiting to retry."
            )

        self._log(f"Action: {action.action_type.value}")
        if action.explanation:
            self._log(f"Explanation: {action.explanation}", "debug")

        # Validate action
        is_valid, error = ActionSpace.validate(action)
        if not is_valid:
            self._log(f"Invalid action: {error}", "warning")

        # Check for action loop BEFORE executing
        if self.history_manager._history and self.history_manager._history.entries:
            from datetime import datetime
            temp_entries = self.history_manager._history.entries.copy()
            temp_entries.append(HistoryEntry(
                step=len(temp_entries) + 1,
                action=action,
                observation=screen_info
            ))
            is_loop, loop_msg = self.history_manager.loop_detector.check_loop(temp_entries)
            if is_loop:
                self._log(f"⚠️ Loop detected: {loop_msg}", "warning")
                
                same_action_count = 0
                for entry in reversed(self.history_manager._history.entries):
                    if self.history_manager.loop_detector._actions_identical(entry.action, action):
                        same_action_count += 1
                    else:
                        break
                
                # 使用 TaskPlan 的建议进行恢复
                task_plan = self.history_manager.task_plan
                if task_plan:
                    recovery_suggestion = task_plan.suggest_recovery(same_action_count)
                    if recovery_suggestion:
                        self._log(f"💡 Recovery suggestion: {recovery_suggestion}", "info")
                        # 记录到执行备注
                        task_plan.execution_notes.append(f"循环检测 ({same_action_count}次): {loop_msg}")
                
                if same_action_count >= 5:
                    self._log(f"❌ Aborting: same action repeated {same_action_count + 1} times", "error")
                    return StepResult(
                        success=False,
                        finished=True,
                        action=Action(
                            action_type=ActionType.ABORT,
                            params={"value": f"Agent stuck in loop: {loop_msg}"},
                            thinking="Detected severe action loop. Aborting task."
                        ),
                        message=f"Task aborted: Agent stuck in loop ({loop_msg})",
                        step_count=step_num
                    )

        # Execute action
        action_result = self.action_handler.execute(action)

        # Record in history
        self.history_manager.add_action(
            action=action,
            observation=screen_info,
            screenshot_base64=screenshot.base64_data,
            user_reply=user_reply
        )

        # Auto-advance sub-task progress based on action success
        if action_result.success and self.history_manager.task_plan:
            self._try_advance_subtask(action, current_app)

        # Check if finished
        finished = action.action_type in (ActionType.COMPLETE, ActionType.ABORT) or action_result.should_finish

        if finished:
            self._log(f"Task finished: {action_result.message or action.params.get('return', 'Done')}")

        return StepResult(
            success=action_result.success,
            finished=finished,
            action=action,
            action_result=action_result,
            message=action_result.message or action.params.get("return"),
            needs_user_input=action_result.requires_user_input,
            user_prompt=action_result.user_prompt,
            session_id=self._current_session_id,
            step_count=step_num
        )

    def _try_advance_subtask(self, action: Action, current_app: dict[str, str] | None) -> None:
        """
        Try to advance to the next sub-task based on action result.
        
        Uses heuristics to determine if current sub-task is likely complete:
        - LAUNCH action completed and app changed to target
        - Navigation actions (CLICK, SWIPE) that likely achieved goal
        - After several successful actions on same sub-task
        """
        task_plan = self.history_manager.task_plan
        if not task_plan or not task_plan.current_sub_task:
            return
        
        current_sub = task_plan.current_sub_task
        should_advance = False
        
        # Check if this action is likely to complete the current sub-task
        if action.action_type == ActionType.LAUNCH:
            # Check if we launched the target app
            if current_sub.app_target and current_app:
                package_name = current_app.get("packageName", "")
                if current_sub.app_target in package_name or package_name in current_sub.app_target:
                    should_advance = True
                    self._log(f"✓ Sub-task {current_sub.id} completed: {current_sub.description}", "debug")
        
        elif action.action_type in (ActionType.CLICK, ActionType.TYPE):
            # For click/type actions, check if description mentions keywords
            desc_lower = current_sub.description.lower()
            action_keywords = {
                "点击": ActionType.CLICK,
                "输入": ActionType.TYPE,
                "搜索": ActionType.TYPE,
                "发送": ActionType.CLICK,
            }
            for keyword, expected_type in action_keywords.items():
                if keyword in desc_lower and action.action_type == expected_type:
                    # Likely completed this sub-task
                    should_advance = True
                    self._log(f"✓ Sub-task {current_sub.id} likely completed: {current_sub.description}", "debug")
                    break
        
        elif action.action_type == ActionType.BACK or action.action_type == ActionType.HOME:
            # Check if sub-task description mentions returning
            desc_lower = current_sub.description.lower()
            if "返回" in desc_lower or "桌面" in desc_lower:
                should_advance = True
                self._log(f"✓ Sub-task {current_sub.id} completed: {current_sub.description}", "debug")
        
        # Also advance if we've done 3+ actions on the same sub-task (heuristic)
        if not should_advance and self.history_manager._history:
            same_subtask_actions = sum(
                1 for e in self.history_manager._history.entries[-5:]
                if e.sub_task_id == current_sub.id
            )
            if same_subtask_actions >= 3:
                # Consider moving to next sub-task after multiple actions
                should_advance = True
                self._log(f"→ Moving to next sub-task after {same_subtask_actions} actions", "debug")
        
        if should_advance:
            self.history_manager.advance_sub_task()
            if task_plan.current_sub_task:
                self._log(f"📍 Current sub-task: {task_plan.current_sub_task.description}")
                # 提醒剩余步骤
                remaining = len(task_plan.remaining_steps)
                if remaining > 0:
                    self._log(f"⚠️ Remaining {remaining} steps", "info")
    
    def _update_plan_from_screen(self, screen_info: str) -> None:
        """
        根据屏幕状态动态更新任务计划。
        
        检测意外情况并调整计划，如：
        - 需要登录
        - 出现弹窗
        - 页面加载中
        """
        task_plan = self.history_manager.task_plan
        if not task_plan:
            return
        
        # 使用 TaskPlan 的 update_from_observation 方法
        suggestion = task_plan.update_from_observation(screen_info, "")
        if suggestion:
            self._log(f"💡 Plan adjustment: {suggestion}", "info")

    def _auto_reply(self, task: str, question: str) -> str:
        """Auto-generate reply to agent's question using LLM."""
        messages = [
            {
                "role": "user",
                "content": f"""你正在帮助用户完成手机上的任务。
任务是：{task}

手机自动化 Agent 询问：{question}

请提供简短、直接的回答来帮助 Agent 继续执行。
只输出答案，不要解释。"""
            }
        ]

        try:
            response = self.llm_client.request(messages, max_tokens=256, temperature=0.5)
            return response.content.strip()
        except Exception:
            return "请继续执行任务。"

    def reset(self) -> None:
        """Reset agent state for a new task."""
        self.history_manager.reset()
        self._current_session_id = None

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get current conversation history as list of dicts."""
        if self.history_manager._history is None:
            return []
        return [
            {
                "step": e.step,
                "action": e.action.to_dict(),
                "observation": e.observation,
                "user_reply": e.user_reply,
            }
            for e in self.history_manager._history.entries
        ]

    @property
    def step_count(self) -> int:
        """Get current step count."""
        return self.history_manager.step_count

    @property
    def current_session(self) -> str | None:
        """Get current session ID."""
        return self._current_session_id
