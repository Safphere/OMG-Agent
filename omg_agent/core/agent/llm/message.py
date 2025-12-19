"""Message builder utilities for LLM conversations."""

from typing import Any


class MessageBuilder:
    """Helper class for building LLM messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str | None = None,
        image_base64: str | None = None,
        image_url: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message, optionally with image.

        Args:
            text: Text content
            image_base64: Base64 encoded image data
            image_url: Image URL (local path or http)

        Returns:
            Message dict
        """
        content: list[dict[str, Any]] = []

        if text:
            content.append({"type": "text", "text": text})

        if image_base64:
            # Detect format from header
            if image_base64.startswith("/9j/"):
                media_type = "image/jpeg"
            else:
                media_type = "image/png"

            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{image_base64}"}
            })
        elif image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # If only text, return simple format
        if len(content) == 1 and content[0]["type"] == "text":
            return {"role": "user", "content": text}

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def build_screen_info(
        current_app: dict[str, str] | None = None,
        orientation: int = 0
    ) -> str:
        """
        Build screen info string.

        Args:
            current_app: Dict with 'package' and 'activity'
            orientation: Screen orientation (0-3)

        Returns:
            Formatted screen info string
        """
        parts = []

        if current_app:
            package = current_app.get("package", "unknown")
            activity = current_app.get("activity", "unknown")
            parts.append(f"Current App: {package}")
            if activity != "unknown":
                parts.append(f"Activity: {activity}")

        orientation_names = ["Portrait", "Landscape (Left)", "Portrait (Upside)", "Landscape (Right)"]
        parts.append(f"Orientation: {orientation_names[orientation % 4]}")

        return "\n".join(parts)

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove images from message to save context space.

        Args:
            message: Message dict

        Returns:
            Message with images removed
        """
        if isinstance(message.get("content"), str):
            return message

        content = message.get("content", [])
        if not isinstance(content, list):
            return message

        # Keep only text content
        new_content = []
        for item in content:
            if item.get("type") == "text":
                new_content.append(item)
            elif item.get("type") == "image_url":
                # Replace with placeholder
                new_content.append({"type": "text", "text": "[Screenshot]"})

        # Simplify if only one text item
        if len(new_content) == 1 and new_content[0]["type"] == "text":
            return {"role": message["role"], "content": new_content[0]["text"]}

        return {"role": message["role"], "content": new_content}

    @staticmethod
    def build_task_prompt(
        task: str,
        history_summary: str = "",
        user_comment: str = "",
        hints: list[str] | None = None,
        lang: str = "zh"
    ) -> str:
        """
        Build task prompt with context.

        Args:
            task: The task description
            history_summary: Summary of previous actions
            user_comment: Additional user instructions
            hints: List of hints/tips
            lang: Language ('zh' or 'en')

        Returns:
            Formatted task prompt
        """
        if lang == "zh":
            return MessageBuilder._build_chinese_task_prompt(
                task, history_summary, user_comment, hints or []
            )
        return MessageBuilder._build_english_task_prompt(
            task, history_summary, user_comment, hints or []
        )

    @staticmethod
    def _build_chinese_task_prompt(
        task: str,
        history_summary: str,
        user_comment: str,
        hints: list[str]
    ) -> str:
        parts = []

        parts.append(f"# 用户任务\n{task}")

        if user_comment:
            parts.append(f"\n# 用户补充指令\n{user_comment}")

        if history_summary:
            parts.append(f"\n# 历史操作总结\n{history_summary}")
        else:
            parts.append("\n# 历史操作总结\n暂无历史操作")

        if hints:
            hints_str = "\n".join(f"- {h}" for h in hints)
            parts.append(f"\n# 提示\n{hints_str}")

        parts.append("\n请分析当前屏幕截图，执行下一步操作完成任务。")

        return "\n".join(parts)

    @staticmethod
    def _build_english_task_prompt(
        task: str,
        history_summary: str,
        user_comment: str,
        hints: list[str]
    ) -> str:
        parts = []

        parts.append(f"# Task\n{task}")

        if user_comment:
            parts.append(f"\n# Additional Instructions\n{user_comment}")

        if history_summary:
            parts.append(f"\n# Action History Summary\n{history_summary}")
        else:
            parts.append("\n# Action History Summary\nNo previous actions")

        if hints:
            hints_str = "\n".join(f"- {h}" for h in hints)
            parts.append(f"\n# Hints\n{hints_str}")

        parts.append("\nAnalyze the current screenshot and perform the next action to complete the task.")

        return "\n".join(parts)
