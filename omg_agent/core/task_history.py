"""
任务历史记录管理模块

提供任务执行历史的保存、加载和查询功能
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from omg_agent.core.config import HISTORY_DIR


@dataclass
class TaskStep:
    """任务步骤记录"""
    
    step_num: int
    action_type: str
    action_params: dict = field(default_factory=dict)
    thinking: str = ""
    result: str = ""
    success: bool = True
    timestamp: str = ""
    screenshot_path: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TaskRecord:
    """任务执行记录"""
    
    task_id: str
    task_name: str
    device_id: str
    start_time: str
    end_time: str = ""
    status: str = "running"  # running, completed, failed, aborted
    total_steps: int = 0
    steps: List[dict] = field(default_factory=list)
    result_summary: str = ""
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]
        if not self.start_time:
            self.start_time = datetime.now().isoformat()
    
    def add_step(self, step: TaskStep) -> None:
        """添加步骤"""
        self.steps.append(asdict(step))
        self.total_steps = len(self.steps)
    
    def finish(self, status: str, summary: str = "") -> None:
        """完成任务"""
        self.status = status
        self.end_time = datetime.now().isoformat()
        self.result_summary = summary
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> TaskRecord:
        """从字典创建"""
        return cls(
            task_id=data.get("task_id", ""),
            task_name=data.get("task_name", ""),
            device_id=data.get("device_id", ""),
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            status=data.get("status", "unknown"),
            total_steps=data.get("total_steps", 0),
            steps=data.get("steps", []),
            result_summary=data.get("result_summary", ""),
        )
    
    def get_display_time(self) -> str:
        """获取显示用的时间"""
        try:
            dt = datetime.fromisoformat(self.start_time)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return self.start_time
    
    def get_duration(self) -> str:
        """获取执行时长"""
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time) if self.end_time else datetime.now()
            duration = end - start
            seconds = int(duration.total_seconds())
            if seconds < 60:
                return f"{seconds}秒"
            elif seconds < 3600:
                return f"{seconds // 60}分{seconds % 60}秒"
            else:
                return f"{seconds // 3600}时{(seconds % 3600) // 60}分"
        except:
            return ""


class TaskHistoryManager:
    """任务历史管理器"""
    
    def __init__(self):
        self._history_dir = HISTORY_DIR
        self._ensure_dir()
        self._current_task: Optional[TaskRecord] = None
    
    def _ensure_dir(self) -> None:
        """确保历史目录存在"""
        self._history_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_task_file(self, task_id: str) -> Path:
        """获取任务文件路径"""
        return self._history_dir / f"task_{task_id}.json"
    
    def start_task(self, task_name: str, device_id: str) -> TaskRecord:
        """开始新任务"""
        self._current_task = TaskRecord(
            task_id=str(uuid.uuid4())[:8],
            task_name=task_name,
            device_id=device_id,
            start_time=datetime.now().isoformat(),
        )
        self._save_current()
        return self._current_task
    
    def add_step(
        self, 
        step_num: int,
        action_type: str,
        action_params: dict = None,
        thinking: str = "",
        result: str = "",
        success: bool = True,
        screenshot_path: str = None
    ) -> None:
        """添加步骤到当前任务"""
        if not self._current_task:
            return
        
        step = TaskStep(
            step_num=step_num,
            action_type=action_type,
            action_params=action_params or {},
            thinking=thinking,
            result=result,
            success=success,
            screenshot_path=screenshot_path,
        )
        self._current_task.add_step(step)
        self._save_current()
    
    def finish_task(self, status: str, summary: str = "") -> None:
        """完成当前任务"""
        if not self._current_task:
            return
        
        self._current_task.finish(status, summary)
        self._save_current()
        self._current_task = None
    
    def _save_current(self) -> None:
        """保存当前任务"""
        if not self._current_task:
            return
        
        file_path = self._get_task_file(self._current_task.task_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self._current_task.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_task(self, task_id: str) -> Optional[TaskRecord]:
        """加载指定任务"""
        file_path = self._get_task_file(task_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return TaskRecord.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None
    
    def list_tasks(self, limit: int = 50) -> List[TaskRecord]:
        """列出历史任务（按时间倒序）"""
        tasks = []
        
        for file_path in self._history_dir.glob("task_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tasks.append(TaskRecord.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        
        # 按开始时间倒序
        tasks.sort(key=lambda t: t.start_time, reverse=True)
        
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """删除指定任务"""
        file_path = self._get_task_file(task_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def clear_all(self) -> int:
        """清空所有历史"""
        count = 0
        for file_path in self._history_dir.glob("task_*.json"):
            file_path.unlink()
            count += 1
        return count
    
    @property
    def current_task(self) -> Optional[TaskRecord]:
        """获取当前任务"""
        return self._current_task


# 全局历史管理器实例
_history_manager: Optional[TaskHistoryManager] = None


def get_history_manager() -> TaskHistoryManager:
    """获取历史管理器单例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = TaskHistoryManager()
    return _history_manager
