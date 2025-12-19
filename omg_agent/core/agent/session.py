"""
Session Manager - Manage agent sessions for task resumption.

Features:
- Unique session IDs for each task
- Session persistence (save/load)
- Session resumption after interruption (e.g., INFO action)
"""

import uuid
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .history import ConversationHistory

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Session state for persistence."""

    session_id: str
    task: str
    status: str  # "running", "paused", "completed", "aborted"
    created_at: str
    updated_at: str

    # Device info
    device_id: str | None = None
    screen_size: tuple[int, int] | None = None

    # Progress
    step_count: int = 0
    history_summary: str = ""

    # For paused sessions (INFO action)
    pending_question: str | None = None

    # Extra metadata
    extra_info: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Manages agent sessions.

    Sessions allow:
    - Tracking multiple concurrent tasks
    - Resuming interrupted tasks
    - Persisting state across restarts
    """

    def __init__(self, storage_dir: str | Path | None = None):
        """
        Initialize session manager.

        Args:
            storage_dir: Directory for session storage. If None, sessions are memory-only.
        """
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._sessions: dict[str, SessionState] = {}

        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_sessions()

    def create_session(
        self,
        task: str,
        device_id: str | None = None,
        extra_info: dict[str, Any] | None = None
    ) -> str:
        """
        Create a new session.

        Args:
            task: Task description
            device_id: Target device ID
            extra_info: Additional metadata

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        state = SessionState(
            session_id=session_id,
            task=task,
            status="running",
            created_at=now,
            updated_at=now,
            device_id=device_id,
            extra_info=extra_info or {}
        )

        self._sessions[session_id] = state
        self._save_session(state)

        return session_id

    def get_session(self, session_id: str) -> SessionState | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        step_count: int | None = None,
        history_summary: str | None = None,
        status: str | None = None,
        pending_question: str | None = None,
        screen_size: tuple[int, int] | None = None
    ) -> None:
        """Update session state."""
        state = self._sessions.get(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")

        if step_count is not None:
            state.step_count = step_count
        if history_summary is not None:
            state.history_summary = history_summary
        if status is not None:
            state.status = status
        if pending_question is not None:
            state.pending_question = pending_question
        if screen_size is not None:
            state.screen_size = screen_size

        state.updated_at = datetime.now().isoformat()
        self._save_session(state)

    def pause_session(self, session_id: str, question: str) -> None:
        """
        Pause session (typically for INFO action).

        Args:
            session_id: Session to pause
            question: Question pending user response
        """
        self.update_session(
            session_id,
            status="paused",
            pending_question=question
        )

    def resume_session(self, session_id: str) -> SessionState | None:
        """
        Resume a paused session.

        Returns:
            Session state if found and was paused, None otherwise
        """
        state = self._sessions.get(session_id)
        if state is None:
            return None

        if state.status == "paused":
            state.status = "running"
            state.pending_question = None
            state.updated_at = datetime.now().isoformat()
            self._save_session(state)

        return state

    def complete_session(self, session_id: str, message: str | None = None) -> None:
        """Mark session as completed."""
        state = self._sessions.get(session_id)
        if state:
            state.status = "completed"
            state.updated_at = datetime.now().isoformat()
            if message:
                state.extra_info["completion_message"] = message
            self._save_session(state)

    def abort_session(self, session_id: str, reason: str | None = None) -> None:
        """Mark session as aborted."""
        state = self._sessions.get(session_id)
        if state:
            state.status = "aborted"
            state.updated_at = datetime.now().isoformat()
            if reason:
                state.extra_info["abort_reason"] = reason
            self._save_session(state)

    def list_sessions(
        self,
        status: str | None = None,
        device_id: str | None = None
    ) -> list[SessionState]:
        """
        List sessions with optional filtering.

        Args:
            status: Filter by status
            device_id: Filter by device

        Returns:
            List of matching sessions
        """
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]
        if device_id:
            sessions = [s for s in sessions if s.device_id == device_id]

        # Sort by updated time, newest first
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self.storage_dir:
                path = self.storage_dir / f"{session_id}.json"
                if path.exists():
                    path.unlink()
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.

        Returns:
            Number of sessions removed
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0

        for session_id, state in list(self._sessions.items()):
            updated = datetime.fromisoformat(state.updated_at)
            if updated < cutoff and state.status in ("completed", "aborted"):
                self.delete_session(session_id)
                removed += 1

        return removed

    def _save_session(self, state: SessionState) -> None:
        """Save session to disk."""
        if self.storage_dir is None:
            return

        path = self.storage_dir / f"{state.session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(state), f, ensure_ascii=False, indent=2)

    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        if self.storage_dir is None:
            return

        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                state = SessionState(**data)
                self._sessions[state.session_id] = state
            except Exception as e:
                logger.warning(f"Failed to load session {path}: {e}")
