"""
OMG-Agent 主窗口模块

提供完整的 GUI 界面
"""

from __future__ import annotations

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
import threading
import io
from PIL import Image
import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QGroupBox,
    QStatusBar,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QSplitter,
    QMessageBox,
    QProgressBar,
    QTabWidget,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSplashScreen,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QBuffer, QByteArray, QIODevice, QEvent
from PyQt6.QtGui import QFont, QAction, QKeySequence, QIcon, QPixmap, QImage

from omg_agent.core.config import (
    Config,
    load_config,
    save_config,
    MODEL_PRESETS,
    QUICK_TASKS,
    SWIPE_GESTURES,
)
from omg_agent.core.task_history import get_history_manager, TaskRecord
from omg_agent.core.i18n import I18n, LANGUAGES, LanguageCode
from omg_agent.gui.themes import THEMES, ThemeName, get_theme, generate_stylesheet
from omg_agent.gui.widgets import PhoneScreen, QuickActionBar, StatusIndicator


# 资源路径 (omg_agent/gui/main_window.py -> root/assets)
ASSETS_PATH = Path(__file__).parent.parent.parent / "assets"


class ScreenCaptureThread(QThread):
    """屏幕捕获线程 - ADB 实时视频流模式
    
    使用 ADB exec-out screencap 实现高帧率捕获
    特性:
    - 可调节帧率 (默认15fps，最高30fps)
    - 异步处理，最小延迟
    - 自动丢弃过时帧，保持流畅
    """

    frame_ready = pyqtSignal(bytes)
    error = pyqtSignal(str)
    fps_updated = pyqtSignal(float)  # 实际帧率反馈

    def __init__(self, device_id: Optional[str] = None, fps: int = 15):
        super().__init__()
        self.device_id = device_id
        self.target_fps = min(fps, 30)  # 限制最大30fps
        self.interval = 1.0 / self.target_fps
        self._running = True
        self._frame_count = 0
        self._last_fps_time = 0

    def run(self) -> None:
        import time
        
        # 构建基础命令
        base_cmd = ["adb"]
        if self.device_id:
            base_cmd.extend(["-s", self.device_id])
        base_cmd.extend(["exec-out", "screencap", "-p"])
        
        self._last_fps_time = time.time()
        last_capture_time = 0
        
        while self._running:
            try:
                current_time = time.time()
                
                # 帧率控制
                elapsed = current_time - last_capture_time
                if elapsed < self.interval:
                    time.sleep(self.interval - elapsed)
                    current_time = time.time()
                
                # 捕获屏幕
                result = subprocess.run(
                    base_cmd, 
                    capture_output=True, 
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                if result.returncode == 0 and result.stdout:
                    self.frame_ready.emit(result.stdout)
                    self._frame_count += 1
                
                last_capture_time = current_time
                
                # 每秒更新一次实际帧率
                fps_elapsed = current_time - self._last_fps_time
                if fps_elapsed >= 1.0:
                    actual_fps = self._frame_count / fps_elapsed
                    self.fps_updated.emit(actual_fps)
                    self._frame_count = 0
                    self._last_fps_time = current_time
                    
            except subprocess.TimeoutExpired:
                # 命令超时，跳过此帧
                continue
            except Exception as e:
                self.error.emit(str(e))
                time.sleep(0.5)  # 错误后短暂暂停

    def stop(self) -> None:
        self._running = False
        self.wait(2000)
    
    def set_fps(self, fps: int) -> None:
        """动态调整帧率"""
        self.target_fps = min(max(fps, 5), 30)
        self.interval = 1.0 / self.target_fps


class AgentThread(QThread):
    """Agent 执行线程"""

    thinking = pyqtSignal(str)
    action = pyqtSignal(str)
    step_done = pyqtSignal(int, bool)
    task_finished = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    # 新增: 步骤记录信号
    step_recorded = pyqtSignal(int, str, str, str, bool)  # step, action_type, thinking, result, success

    def __init__(self, task: str, config: dict, screenshot_provider: Optional[callable] = None):
        super().__init__()
        self.task = task
        self.config = config
        self.screenshot_provider = screenshot_provider
        self._stop = False
        self._paused = False
        self._history_mgr = get_history_manager()

    def run(self) -> None:
        try:
            # Use new agent module (no autoglm dependency)
            from omg_agent.core.agent import PhoneAgent, AgentConfig
            from omg_agent.core.agent.llm import LLMConfig
            import time

            # 开始记录任务历史
            device_id = self.config.get("device_id", "unknown")
            self._history_mgr.start_task(self.task, device_id)

            llm_cfg = LLMConfig(
                api_base=self.config.get("api_url", "http://localhost:8000/v1"),
                api_key=self.config.get("api_key", "EMPTY"),
                model=self.config.get("model_name", "autoglm-phone-9b"),
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 4096),
                lang=self.config.get("lang", "zh"),
            )

            agent_cfg = AgentConfig(
                max_steps=100,  # Use default, removed from UI
                step_delay=self.config.get("step_delay", 1.0),
                device_id=self.config.get("device_id"),
                lang=self.config.get("lang", "zh"),
                auto_wake_screen=self.config.get("auto_wake", True),
                reset_to_home=self.config.get("reset_home", True),
                verbose=True,
            )

            agent = PhoneAgent(
                llm_config=llm_cfg,
                agent_config=agent_cfg,
                screenshot_provider=self.screenshot_provider,
                logger=self.log.emit
            )
            result = agent.step(self.task)
            step = 1

            while not result.finished and not self._stop:
                # Handle pause
                while self._paused and not self._stop:
                    time.sleep(0.1)

                if self._stop:
                    break

                thinking_text = ""
                action_str = ""
                action_type = ""
                action_params = {}

                if result.thinking:
                    thinking_text = str(result.thinking) if not isinstance(result.thinking, str) else result.thinking
                    self.thinking.emit(thinking_text)
                
                if result.action:
                    action_type = result.action.action_type.value if hasattr(result.action.action_type, 'value') else str(result.action.action_type)
                    action_params = result.action.params if hasattr(result.action, 'params') else {}
                    action_data = result.action.to_dict() if hasattr(result.action, 'to_dict') else result.action
                    action_str = (
                        json.dumps(action_data, ensure_ascii=False, indent=2)
                        if isinstance(action_data, dict)
                        else str(action_data)
                    )
                    self.action.emit(action_str)

                # 记录步骤到历史
                self._history_mgr.add_step(
                    step_num=step,
                    action_type=action_type,
                    action_params=action_params,
                    thinking=thinking_text,
                    result=result.message or "",
                    success=result.success,
                )

                self.step_done.emit(step, result.success)
                self.step_recorded.emit(step, action_type, thinking_text[:100], result.message or "", result.success)
                
                result = agent.step()
                step += 1

            # 完成任务记录
            if self._stop:
                self._history_mgr.finish_task("aborted", "任务已停止")
                self.task_finished.emit("任务已停止")
            else:
                status = "completed" if result.success else "failed"
                self._history_mgr.finish_task(status, result.message or "任务完成")
                self.task_finished.emit(result.message or "任务完成")

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self._history_mgr.finish_task("failed", str(e))
            self.error.emit(error_msg)

    def stop(self) -> None:
        self._stop = True

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False


class WirelessConnectDialog(QDialog):
    """无线连接对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._s = I18n.get_strings()
        self.setWindowTitle(self._s.wireless_title)
        self.setMinimumWidth(400)
        self._address = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        s = self._s
        layout = QVBoxLayout(self)

        # 说明
        info = QLabel(s.wireless_info)
        info.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(info)

        # IP 和端口输入
        form = QFormLayout()

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        form.addRow(s.wireless_ip, self.ip_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(5555)
        form.addRow(s.wireless_port, self.port_input)

        layout.addLayout(form)

        # 快捷操作
        quick_group = QGroupBox(s.wireless_quick)
        quick_layout = QVBoxLayout(quick_group)

        btn_enable_tcpip = QPushButton(s.wireless_enable_tcpip)
        btn_enable_tcpip.clicked.connect(self._enable_tcpip)
        quick_layout.addWidget(btn_enable_tcpip)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        quick_layout.addWidget(self.status_label)

        layout.addWidget(quick_group)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_connect)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _enable_tcpip(self) -> None:
        """启用 TCP/IP 模式"""
        s = self._s
        try:
            result = subprocess.run(
                ["adb", "tcpip", "5555"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10,
            )
            if result.returncode == 0:
                self.status_label.setText(s.wireless_tcpip_ok)
                self.status_label.setStyleSheet("color: #4CAF50;")
            else:
                self.status_label.setText(s.wireless_tcpip_fail.format(result.stderr))
                self.status_label.setStyleSheet("color: #f44336;")
        except Exception as e:
            self.status_label.setText(s.wireless_tcpip_fail.format(str(e)))
            self.status_label.setStyleSheet("color: #f44336;")

    def _on_connect(self) -> None:
        """连接设备"""
        s = self._s
        ip = self.ip_input.text().strip()
        port = self.port_input.value()

        if not ip:
            QMessageBox.warning(self, s.notice, s.wireless_enter_ip)
            return

        self._address = f"{ip}:{port}"
        self.accept()

    def get_address(self) -> str:
        return self._address


class ModelConfigDialog(QDialog):
    """模型配置对话框 - 支持多配置档案管理"""

    def __init__(self, config: dict, parent: Optional[QWidget] = None, saved_profiles: dict = None):
        super().__init__(parent)
        self._s = I18n.get_strings()
        self.config = config.copy()
        self.saved_profiles = saved_profiles or {}  # 已保存的自定义配置
        self.setWindowTitle(self._s.model_config)
        self.setMinimumWidth(550)
        self._setup_ui()
        self._load_current_profile()

    def _setup_ui(self) -> None:
        s = self._s
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # === 配置档案选择 ===
        profile_group = QGroupBox("配置档案")
        profile_layout = QHBoxLayout(profile_group)
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self._refresh_profile_list()
        self.profile_combo.currentTextChanged.connect(self._on_profile_change)
        profile_layout.addWidget(self.profile_combo, stretch=1)
        
        # 保存当前配置按钮
        self.btn_save_profile = QPushButton("💾 保存")
        self.btn_save_profile.setToolTip("保存当前配置为新档案")
        self.btn_save_profile.clicked.connect(self._save_profile)
        profile_layout.addWidget(self.btn_save_profile)
        
        # 删除配置按钮
        self.btn_delete_profile = QPushButton("🗑️")
        self.btn_delete_profile.setToolTip("删除当前配置档案")
        self.btn_delete_profile.setFixedWidth(40)
        self.btn_delete_profile.clicked.connect(self._delete_profile)
        profile_layout.addWidget(self.btn_delete_profile)
        
        layout.addWidget(profile_group)

        # === 预设模板 ===
        preset_group = QGroupBox(s.model_preset)
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["选择预设模板..."] + list(MODEL_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self._on_preset_change)
        preset_layout.addWidget(self.preset_combo)
        layout.addWidget(preset_group)

        # === 基本配置 ===
        custom_group = QGroupBox(s.model_detail)
        form = QFormLayout(custom_group)

        # 配置名称
        self.profile_name_input = QLineEdit(self.config.get("profile_name", "自定义"))
        self.profile_name_input.setPlaceholderText("输入配置名称")
        form.addRow("配置名称", self.profile_name_input)

        self.base_url_input = QLineEdit(self.config.get("api_url", ""))
        self.base_url_input.setPlaceholderText("http://localhost:8000/v1")
        form.addRow(s.model_url, self.base_url_input)

        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setPlaceholderText("EMPTY")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(s.model_key, self.api_key_input)

        self.model_name_input = QLineEdit(self.config.get("model_name", ""))
        self.model_name_input.setPlaceholderText("autoglm-phone-9b")
        form.addRow(s.model_name, self.model_name_input)

        layout.addWidget(custom_group)

        # === 高级设置 (可折叠) ===
        self.advanced_toggle = QPushButton(f"▶ {s.model_advanced}")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #21262d;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
            QPushButton:checked {
                background-color: #30363d;
            }
        """)
        self.advanced_toggle.clicked.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_toggle)

        # 高级设置内容容器
        self.advanced_container = QWidget()
        advanced_form = QFormLayout(self.advanced_container)
        advanced_form.setContentsMargins(10, 10, 10, 10)

        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 2.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(self.config.get("temperature", 0.7))
        advanced_form.addRow(s.model_temperature, self.temperature_input)

        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(256, 16384)
        self.max_tokens_input.setSingleStep(256)
        self.max_tokens_input.setValue(self.config.get("max_tokens", 4096))
        advanced_form.addRow(s.model_max_tokens, self.max_tokens_input)

        self.step_delay_input = QDoubleSpinBox()
        self.step_delay_input.setRange(0.0, 5.0)
        self.step_delay_input.setSingleStep(0.5)
        self.step_delay_input.setValue(self.config.get("step_delay", 1.0))
        advanced_form.addRow(s.model_step_delay, self.step_delay_input)

        self.auto_wake_checkbox = QCheckBox()
        self.auto_wake_checkbox.setChecked(self.config.get("auto_wake", True))
        advanced_form.addRow(s.model_auto_wake, self.auto_wake_checkbox)

        self.reset_home_checkbox = QCheckBox()
        self.reset_home_checkbox.setChecked(self.config.get("reset_home", True))
        advanced_form.addRow(s.model_reset_home, self.reset_home_checkbox)

        self.advanced_container.setVisible(False)  # 默认折叠
        layout.addWidget(self.advanced_container)

        # === 按钮 ===
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_profile_list(self) -> None:
        """刷新配置档案列表"""
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        
        # 添加已保存的配置
        profiles = list(self.saved_profiles.keys())
        if not profiles:
            profiles = ["自定义"]
        self.profile_combo.addItems(profiles)
        
        # 选中当前配置
        current = self.config.get("profile_name", "自定义")
        idx = self.profile_combo.findText(current)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        
        self.profile_combo.blockSignals(False)

    def _load_current_profile(self) -> None:
        """加载当前配置到 UI"""
        self.profile_name_input.setText(self.config.get("profile_name", "自定义"))
        self.base_url_input.setText(self.config.get("api_url", ""))
        self.api_key_input.setText(self.config.get("api_key", ""))
        self.model_name_input.setText(self.config.get("model_name", ""))
        self.temperature_input.setValue(self.config.get("temperature", 0.7))
        self.max_tokens_input.setValue(self.config.get("max_tokens", 4096))
        self.step_delay_input.setValue(self.config.get("step_delay", 1.0))
        self.auto_wake_checkbox.setChecked(self.config.get("auto_wake", True))
        self.reset_home_checkbox.setChecked(self.config.get("reset_home", True))

    def _on_profile_change(self, profile_name: str) -> None:
        """切换配置档案"""
        if profile_name in self.saved_profiles:
            profile = self.saved_profiles[profile_name]
            self.profile_name_input.setText(profile.get("name", profile_name))
            self.base_url_input.setText(profile.get("base_url", ""))
            self.api_key_input.setText(profile.get("api_key", ""))
            self.model_name_input.setText(profile.get("model_name", ""))
            self.temperature_input.setValue(profile.get("temperature", 0.7))
            self.max_tokens_input.setValue(profile.get("max_tokens", 4096))
            self.step_delay_input.setValue(profile.get("step_delay", 1.0))
            self.auto_wake_checkbox.setChecked(profile.get("auto_wake", True))
            self.reset_home_checkbox.setChecked(profile.get("reset_home", True))

    def _on_preset_change(self, preset_name: str) -> None:
        """应用预设模板"""
        if preset_name in MODEL_PRESETS:
            preset = MODEL_PRESETS[preset_name]
            self.profile_name_input.setText(preset_name)
            self.base_url_input.setText(preset.base_url)
            self.model_name_input.setText(preset.model_name)
            # 不覆盖 API Key，让用户自己填写

    def _save_profile(self) -> None:
        """保存当前配置为新档案"""
        name = self.profile_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入配置名称")
            return
        
        # 保存到 saved_profiles
        self.saved_profiles[name] = {
            "name": name,
            "base_url": self.base_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "model_name": self.model_name_input.text().strip(),
            "temperature": self.temperature_input.value(),
            "max_tokens": self.max_tokens_input.value(),
            "step_delay": self.step_delay_input.value(),
            "auto_wake": self.auto_wake_checkbox.isChecked(),
            "reset_home": self.reset_home_checkbox.isChecked(),
        }
        
        self._refresh_profile_list()
        self.profile_combo.setCurrentText(name)
        QMessageBox.information(self, "成功", f"配置 '{name}' 已保存")

    def _delete_profile(self) -> None:
        """删除当前配置档案"""
        name = self.profile_combo.currentText()
        if name == "自定义":
            QMessageBox.warning(self, "提示", "默认配置不能删除")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除配置 '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.saved_profiles:
                del self.saved_profiles[name]
            self._refresh_profile_list()

    def _toggle_advanced(self) -> None:
        """切换高级设置面板的显示/隐藏"""
        s = self._s
        is_expanded = self.advanced_toggle.isChecked()
        self.advanced_container.setVisible(is_expanded)
        arrow = "▼" if is_expanded else "▶"
        self.advanced_toggle.setText(f"{arrow} {s.model_advanced}")
        self.adjustSize()

    def get_config(self) -> dict:
        return {
            "profile_name": self.profile_name_input.text().strip() or "自定义",
            "api_url": self.base_url_input.text().strip() or "http://localhost:8000/v1",
            "api_key": self.api_key_input.text().strip() or "EMPTY",
            "model_name": self.model_name_input.text().strip() or "autoglm-phone-9b",
            "temperature": self.temperature_input.value(),
            "max_tokens": self.max_tokens_input.value(),
            "step_delay": self.step_delay_input.value(),
            "auto_wake": self.auto_wake_checkbox.isChecked(),
            "reset_home": self.reset_home_checkbox.isChecked(),
        }

    def get_saved_profiles(self) -> dict:
        """获取所有保存的配置档案"""
        return self.saved_profiles


class EnhancedMainWindow(QMainWindow):
    """OMG-Agent 主窗口"""

    frame_received = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        # 加载配置
        self._config = load_config()
        self._current_theme: ThemeName = self._config.ui.theme
        self._current_lang: LanguageCode = self._config.ui.language
        I18n.set_language(self._current_lang)
        
        # 设置窗口
        self.setWindowTitle("OMG-Agent")
        self.setMinimumSize(1280, 800)
        self._set_window_icon()

        # 模型配置 (从当前配置档案加载)
        current_model = self._config.model
        self.model_config = {
            "profile_name": self._config.current_profile,
            "api_url": current_model.base_url,
            "api_key": current_model.api_key,
            "model_name": current_model.model_name,
            "max_steps": current_model.max_steps,
            "temperature": current_model.temperature,
            "max_tokens": current_model.max_tokens,
            "step_delay": current_model.step_delay,
            "auto_wake": current_model.auto_wake,
            "reset_home": current_model.reset_home,
        }

        # 线程
        self.capture_thread: Optional[ScreenCaptureThread] = None
        self.agent_thread: Optional[AgentThread] = None
        self.current_device: Optional[str] = None

        # 任务历史
        self._task_history: list = []
        self._current_task_record: Optional[dict] = None


        # Frame Cache for AI
        self._frame_cache: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()



        # 构建界面
        self._apply_theme()
        self._create_menu()
        self._create_ui()
        self._create_statusbar()

        # 信号连接
        self.frame_received.connect(self._update_frame_display)
        self._request_screenshot_signal.connect(self._on_screenshot_requested)

        # 初始化
        self._refresh_devices()

    def _set_window_icon(self) -> None:
        """设置窗口图标"""
        logo_path = ASSETS_PATH / "logo.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

    @property
    def _s(self):
        """获取当前语言字符串"""
        return I18n.get_strings()

    def _save_config(self) -> None:
        """保存配置到用户目录"""
        from omg_agent.core.config import ModelProfile, UIConfig, save_config
        
        # 获取配置名称 (从预设或自定义)
        profile_name = self.model_config.get("profile_name", "自定义")
        
        # 创建模型配置档案
        profile = ModelProfile(
            name=profile_name,
            base_url=self.model_config.get("api_url", "http://localhost:8000/v1"),
            api_key=self.model_config.get("api_key", "EMPTY"),
            model_name=self.model_config.get("model_name", "autoglm-phone-9b"),
            max_steps=self.model_config.get("max_steps", 30),
            temperature=self.model_config.get("temperature", 0.7),
            max_tokens=self.model_config.get("max_tokens", 4096),
            step_delay=self.model_config.get("step_delay", 1.0),
            auto_wake=self.model_config.get("auto_wake", True),
            reset_home=self.model_config.get("reset_home", True),
        )
        
        # 保存到配置
        self._config.set_model(profile)
        self._config.ui = UIConfig(
            theme=self._current_theme,
            language=self._current_lang,
        )
        self._config.last_device = self.current_device
        
        # 保存到文件
        save_config(self._config)

    def _apply_theme(self) -> None:
        """应用主题"""
        theme = get_theme(self._current_theme)
        self.setStyleSheet(generate_stylesheet(theme))

    def _create_menu(self) -> None:
        """创建菜单栏"""
        s = I18n.get_strings()
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu(s.file)

        model_action = QAction(s.model_config, self)
        model_action.setShortcut(QKeySequence("Ctrl+M"))
        model_action.triggered.connect(self._show_model_config)
        file_menu.addAction(model_action)

        file_menu.addSeparator()

        exit_action = QAction(s.exit, self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设备菜单
        device_menu = menubar.addMenu(s.device)

        refresh_action = QAction(s.refresh_devices, self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._refresh_devices)
        device_menu.addAction(refresh_action)

        wireless_action = QAction(s.wireless_connect, self)
        wireless_action.triggered.connect(self._show_wireless_connect)
        device_menu.addAction(wireless_action)

        disconnect_action = QAction(s.disconnect_all, self)
        disconnect_action.triggered.connect(self._disconnect_all)
        device_menu.addAction(disconnect_action)

        # 视图菜单
        view_menu = menubar.addMenu(s.view)

        # 主题子菜单
        theme_menu = view_menu.addMenu(s.theme)
        
        self._dark_action = QAction(s.dark_theme, self)
        self._dark_action.setCheckable(True)
        self._dark_action.setChecked(self._current_theme == "dark")
        self._dark_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(self._dark_action)

        self._light_action = QAction(s.light_theme, self)
        self._light_action.setCheckable(True)
        self._light_action.setChecked(self._current_theme == "light")
        self._light_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(self._light_action)

        # 语言子菜单
        lang_menu = view_menu.addMenu(s.language)

        self._zh_action = QAction("中文", self)
        self._zh_action.setCheckable(True)
        self._zh_action.setChecked(self._current_lang == "zh")
        self._zh_action.triggered.connect(lambda: self._set_language("zh"))
        lang_menu.addAction(self._zh_action)

        self._en_action = QAction("English", self)
        self._en_action.setCheckable(True)
        self._en_action.setChecked(self._current_lang == "en")
        self._en_action.triggered.connect(lambda: self._set_language("en"))
        lang_menu.addAction(self._en_action)

        # 帮助菜单
        help_menu = menubar.addMenu(s.help)

        about_action = QAction(s.about, self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_ui(self) -> None:
        """创建主界面"""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)  # 加宽拖动条，更容易拖动
        self.splitter.setChildrenCollapsible(False)  # 禁止子组件折叠
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
            }
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
            QSplitter::handle:pressed {
                background-color: #1f6feb;
            }
        """)

        phone_container = QWidget()
        phone_container.setMinimumWidth(300)  # 投屏区域最小宽度
        phone_container_layout = QVBoxLayout(phone_container)
        # 移除边距，最大化显示区域
        phone_container_layout.setContentsMargins(0, 0, 0, 0)
        phone_container_layout.setSpacing(0)

        self.phone_screen = PhoneScreen()
        self.phone_screen.clicked.connect(self._on_tap)
        self.phone_screen.swiped.connect(self._on_swipe)

        phone_container_layout.addWidget(self.phone_screen, 1)

        self.splitter.addWidget(phone_container)

        # 右侧 - 控制面板
        right_panel = self._create_control_panel()
        self.splitter.addWidget(right_panel)

        # 设置 stretch factor: 左侧投屏区域占更大比例
        self.splitter.setStretchFactor(0, 2)  # 左侧投屏区域
        self.splitter.setStretchFactor(1, 1)  # 右侧控制面板

        # 初始大小: 投屏占 60%，控制面板占 40%
        self.splitter.setSizes([720, 480])
        main_layout.addWidget(self.splitter)

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        s = I18n.get_strings()
        panel = QWidget()
        panel.setMinimumWidth(350)  # 最小宽度
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # 投屏控制
        self.screen_group = QGroupBox(s.screen_control)
        screen_layout = QVBoxLayout(self.screen_group)
        screen_layout.setSpacing(6)
        screen_layout.setContentsMargins(10, 14, 10, 10)

        # 设备选择
        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(32)
        self.device_combo.currentTextChanged.connect(self._on_device_change)
        device_row.addWidget(self.device_combo, stretch=1)

        self.btn_refresh = QPushButton(s.refresh)
        self.btn_refresh.setMinimumHeight(32)
        self.btn_refresh.setFixedWidth(60)
        self.btn_refresh.clicked.connect(self._refresh_devices)
        device_row.addWidget(self.btn_refresh)
        screen_layout.addLayout(device_row)

        # 截屏控制
        control_row = QHBoxLayout()
        control_row.setSpacing(6)
        
        # 手动截屏按钮
        self.btn_screenshot = QPushButton("📷 截屏")
        self.btn_screenshot.setObjectName("primary")
        self.btn_screenshot.setMinimumHeight(32)
        self.btn_screenshot.setToolTip("手动截取当前屏幕（AI执行时会自动更新）")
        self.btn_screenshot.clicked.connect(self._manual_screenshot)
        control_row.addWidget(self.btn_screenshot, stretch=1)

        # 实时投屏开关（低帧率，省资源）
        self.btn_start_screen = QPushButton("▶ 投屏")
        self.btn_start_screen.setMinimumHeight(32)
        self.btn_start_screen.setToolTip("开启实时投屏 (8fps)")
        self.btn_start_screen.clicked.connect(self._start_capture)
        control_row.addWidget(self.btn_start_screen, stretch=1)

        self.btn_stop_screen = QPushButton("⏹")
        self.btn_stop_screen.setObjectName("danger")
        self.btn_stop_screen.setMinimumHeight(32)
        self.btn_stop_screen.setFixedWidth(40)
        self.btn_stop_screen.setToolTip("停止投屏")
        self.btn_stop_screen.clicked.connect(self._stop_capture)
        self.btn_stop_screen.setEnabled(False)
        control_row.addWidget(self.btn_stop_screen)
        screen_layout.addLayout(control_row)

        # 快捷操作
        action_row = QHBoxLayout()
        self.quick_bar = QuickActionBar()
        self.quick_bar.action_triggered.connect(self._on_quick_action)
        action_row.addWidget(self.quick_bar)
        self.status_indicator = StatusIndicator()
        action_row.addWidget(self.status_indicator)
        screen_layout.addLayout(action_row)

        layout.addWidget(self.screen_group)

        # AI 任务
        self.task_group = QGroupBox(s.ai_task)
        task_layout = QVBoxLayout(self.task_group)
        task_layout.setSpacing(6)
        task_layout.setContentsMargins(10, 14, 10, 10)

        # 预设任务
        self.quick_combo = QComboBox()
        self.quick_combo.setMinimumHeight(32)
        self.quick_combo.addItems([s.select_preset] + QUICK_TASKS)
        self.quick_combo.currentTextChanged.connect(self._on_quick_task)
        task_layout.addWidget(self.quick_combo)

        # 任务输入
        self.task_input = QLineEdit()
        self.task_input.setMinimumHeight(32)
        self.task_input.setPlaceholderText(s.input_task)
        self.task_input.returnPressed.connect(self._start_task)
        task_layout.addWidget(self.task_input)

        # 执行按钮
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton(s.execute)
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumHeight(32)
        self.btn_start.clicked.connect(self._start_task)
        btn_layout.addWidget(self.btn_start, stretch=2)

        self.btn_pause = QPushButton(s.pause)
        self.btn_pause.setMinimumHeight(32)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_pause.setEnabled(False)
        btn_layout.addWidget(self.btn_pause, stretch=1)

        self.btn_stop = QPushButton(s.stop)
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setMinimumHeight(32)
        self.btn_stop.clicked.connect(self._stop_task)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop, stretch=1)
        task_layout.addLayout(btn_layout)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setMinimumHeight(4)
        task_layout.addWidget(self.progress)

        layout.addWidget(self.task_group)

        # 输出标签页
        self.output_tabs = QTabWidget()

        # 日志视图 (放在第一个)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit {
                font-family: 'Cascadia Code', Consolas, monospace;
                font-size: 12px;
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #161b22;
                color: #8b949e;
                padding: 8px;
            }
        """)
        self.output_tabs.addTab(self.log_view, s.logs)

        # 思考视图 (放在第二个)
        self.thinking_view = QTextEdit()
        self.thinking_view.setReadOnly(True)
        self.thinking_view.setStyleSheet("""
            QTextEdit {
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 13px;
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #161b22;
                color: #c9d1d9;
                padding: 8px;
            }
        """)
        self.output_tabs.addTab(self.thinking_view, s.thinking)

        # 历史视图 - 使用列表+详情的组合视图
        self.history_widget = QWidget()
        history_layout = QVBoxLayout(self.history_widget)
        history_layout.setSpacing(6)
        history_layout.setContentsMargins(0, 0, 0, 0)
        
        # 历史任务列表
        self.history_list = QComboBox()
        self.history_list.setMinimumHeight(32)
        self.history_list.currentIndexChanged.connect(self._on_history_select)
        history_layout.addWidget(self.history_list)
        
        # 历史操作按钮
        history_btn_row = QHBoxLayout()
        self.btn_refresh_history = QPushButton("🔄 刷新")
        self.btn_refresh_history.clicked.connect(self._refresh_history_list)
        history_btn_row.addWidget(self.btn_refresh_history)
        
        self.btn_delete_history = QPushButton("🗑️ 删除")
        self.btn_delete_history.clicked.connect(self._delete_current_history)
        history_btn_row.addWidget(self.btn_delete_history)
        
        self.btn_clear_history = QPushButton("清空全部")
        self.btn_clear_history.clicked.connect(self._clear_all_history)
        history_btn_row.addWidget(self.btn_clear_history)
        history_layout.addLayout(history_btn_row)
        
        # 历史详情视图
        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setStyleSheet("""
            QTextEdit {
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
                border: 1px solid #30363d;
                border-radius: 6px;
                background-color: #161b22;
                color: #c9d1d9;
                padding: 8px;
            }
        """)
        history_layout.addWidget(self.history_view, stretch=1)
        
        self.output_tabs.addTab(self.history_widget, s.history)
        
        # 初始加载历史列表
        self._refresh_history_list()

        layout.addWidget(self.output_tabs, stretch=1)

        # 清空按钮
        self.btn_clear = QPushButton(s.clear)
        self.btn_clear.setMinimumHeight(28)
        self.btn_clear.clicked.connect(self._clear_output)
        layout.addWidget(self.btn_clear)

        return panel

    def _create_statusbar(self) -> None:
        """创建状态栏"""
        s = I18n.get_strings()
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(s.ready)

    # === 设备管理 ===

    def _refresh_devices(self) -> None:
        s = self._s
        self.device_combo.clear()
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")[1:]
            devices = [line.split("\t")[0] for line in lines if "\tdevice" in line]

            if devices:
                self.device_combo.addItems(devices)
                self.current_device = devices[0]
                self._log(s.log_found_devices.format(len(devices)))
                self.status_indicator.set_status("connected", s.status_connected.format(devices[0]))
            else:
                self.device_combo.addItem(s.no_device)
                self.status_indicator.set_status("disconnected", s.status_disconnected)

        except Exception as e:
            self._log(s.log_refresh_failed.format(e))
            self.status_indicator.set_status("error", s.log_adb_error)

    def _on_device_change(self, device: str) -> None:
        """设备切换时更新状态"""
        s = self._s
        if device and s.no_device not in device:
            self.current_device = device
            self._log(s.log_switch_device.format(device))
            # 更新状态指示器
            self.status_indicator.set_status("connected", s.status_connected.format(device))

    def _show_wireless_connect(self) -> None:
        """显示无线连接对话框"""
        dialog = WirelessConnectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            address = dialog.get_address()
            if address:
                self._connect_wireless(address)

    def _connect_wireless(self, address: str) -> None:
        """连接无线设备"""
        s = self._s
        self._log(s.log_connecting.format(address))
        try:
            result = subprocess.run(
                ["adb", "connect", address],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if "connected" in result.stdout.lower():
                self._log(s.log_connected.format(address))
                self._refresh_devices()
            else:
                self._log(s.log_connect_failed.format(result.stdout + result.stderr))
                QMessageBox.warning(self, s.connect_failed, s.cannot_connect.format(address))

        except Exception as e:
            self._log(s.log_connect_error.format(e))
            QMessageBox.critical(self, s.error, str(e))

    def _disconnect_all(self) -> None:
        """断开所有无线设备"""
        s = self._s
        try:
            subprocess.run(["adb", "disconnect"], timeout=5)
            self._log(s.log_disconnected_all)
            self._refresh_devices()
        except Exception as e:
            self._log(s.log_disconnect_failed.format(e))

    # === 投屏 ===

    def _get_device_screen_size(self) -> Optional[tuple]:
        """获取设备真实屏幕尺寸"""
        if not self.current_device:
            return None
        try:
            result = subprocess.run(
                ["adb", "-s", self.current_device, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # 解析输出：Physical size: 1080x2400
            output = result.stdout.strip()
            if "Physical size:" in output:
                size_str = output.split("Physical size:")[-1].strip()
                width, height = map(int, size_str.split("x"))
                return (width, height)
            elif "Override size:" in output:
                # 如果有 Override，使用 Override
                for line in output.split("\n"):
                    if "Override size:" in line:
                        size_str = line.split("Override size:")[-1].strip()
                        width, height = map(int, size_str.split("x"))
                        return (width, height)
        except Exception as e:
            print(f"Get screen size failed: {e}")
        return None

    def _manual_screenshot(self) -> None:
        """手动截取一帧屏幕"""
        s = self._s
        if not self.current_device:
            QMessageBox.warning(self, s.notice, s.please_connect_device)
            return
        
        try:
            from omg_agent.core.agent.device import get_screenshot
            import base64
            
            screenshot = get_screenshot(self.current_device)
            if screenshot:
                img_data = base64.b64decode(screenshot.base64_data)
                self.phone_screen.update_frame(img_data)
                self._log("📷 截屏完成")
            else:
                self._log("❌ 截屏失败")
        except Exception as e:
            self._log(f"截屏错误: {e}")

    def _start_capture(self) -> None:
        """开始 ADB 实时投屏（低帧率模式，节省资源）"""
        s = self._s
        if not self.current_device:
            QMessageBox.warning(self, s.notice, s.please_connect_device)
            return

        # 获取设备真实屏幕尺寸
        real_screen_size = self._get_device_screen_size()
        if real_screen_size:
            self.phone_screen.set_screen_size(real_screen_size[0], real_screen_size[1])
            self._log(f"Screen size: {real_screen_size[0]}x{real_screen_size[1]}")

        # 使用 ADB 实时视频流模式 (8fps，低帧率省资源)
        self.capture_thread = ScreenCaptureThread(
            device_id=self.current_device,
            fps=8,  # 低帧率，省资源，AI执行时会自动更新
        )
        self.capture_thread.frame_ready.connect(self.phone_screen.update_frame)
        self.capture_thread.error.connect(lambda e: self._log(s.log_screen_error.format(e)))
        self.capture_thread.fps_updated.connect(self._on_fps_update)
        self.capture_thread.start()

        self.btn_start_screen.setEnabled(False)
        self.btn_stop_screen.setEnabled(True)
        self.status_indicator.set_status("connected", "投屏中...")
        self._log("▶ 开始投屏 (8fps)")
    
    def _on_fps_update(self, fps: float) -> None:
        """更新 FPS 显示"""
        self.status_indicator.set_status("connected", f"投屏中 ({fps:.1f} FPS)")

    def _stop_capture(self) -> None:
        """停止截图"""
        s = self._s
        
        # 停止 ADB 截图线程
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread = None
            self._log(s.log_stop_screen)

        self.btn_start_screen.setEnabled(True)
        self.btn_stop_screen.setEnabled(False)
        self.status_indicator.set_status("connected", s.status_screen_stopped)

    def _update_frame_display(self, frame) -> None:
        """更新帧显示"""
        try:
            from PyQt6.QtGui import QImage, QPixmap

            if frame is None:
                return

            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.phone_screen.update_frame(pixmap)
        except Exception as e:
            print(f"Frame display error: {e}")

    # === 手势 ===

    def _on_tap(self, x: int, y: int) -> None:
        s = self._s
        self._adb_input("tap", str(x), str(y))
        self._log(s.log_tap.format(x, y))

    def _on_swipe(self, x1: int, y1: int, x2: int, y2: int) -> None:
        s = self._s
        self._adb_input("swipe", str(x1), str(y1), str(x2), str(y2), "300")
        self._log(s.log_swipe.format(x1, y1, x2, y2))

    def _on_quick_action(self, action: str) -> None:
        s = self._s
        if action == "back":
            self._adb_keyevent("KEYCODE_BACK")
            self._log(s.log_back)
        elif action == "home":
            self._adb_keyevent("KEYCODE_HOME")
            self._log(s.log_home)
        elif action == "recent":
            self._adb_keyevent("KEYCODE_APP_SWITCH")
            self._log(s.log_recent)
        elif action.startswith("swipe_"):
            action_map = {
                "swipe_up": (s.log_swipe_up, "上滑"),
                "swipe_down": (s.log_swipe_down, "下滑"),
                "swipe_left": (s.log_swipe_left, "左滑"),
                "swipe_right": (s.log_swipe_right, "右滑"),
            }
            log_name, gesture_key = action_map.get(action, ("", ""))
            gesture = SWIPE_GESTURES.get(gesture_key)
            if gesture:
                size = self.phone_screen.get_screen_size()
                x1 = int(gesture["start"][0] * size[0] / 1000)
                y1 = int(gesture["start"][1] * size[1] / 1000)
                x2 = int(gesture["end"][0] * size[0] / 1000)
                y2 = int(gesture["end"][1] * size[1] / 1000)
                self._adb_input("swipe", str(x1), str(y1), str(x2), str(y2), "300")
                self._log(log_name)

    def _adb_input(self, *args) -> None:
        s = self._s
        if not self.current_device:
            return
        try:
            cmd = ["adb", "-s", self.current_device, "shell", "input"] + list(args)
            subprocess.run(cmd, timeout=2)
        except Exception as e:
            self._log(s.log_adb_failed.format(e))

    def _adb_keyevent(self, key: str) -> None:
        self._adb_input("keyevent", key)

    # 截图请求信号 ((result_container, event))
    _request_screenshot_signal = pyqtSignal(object)

    def _get_screenshot_from_ui(self) -> Any:
        """从 UI 获取当前屏幕截图 (线程安全封装)"""
        # 如果已经在主线程，直接执行
        if QThread.currentThread() == self.thread():
            return self._capture_screenshot_impl()

        # 如果在工作线程，通过信号调度到主线程执行
        result_container = {}
        event = threading.Event()
        
        # 发送请求信号
        self._request_screenshot_signal.emit((result_container, event))
        
        # 等待主线程完成
        event.wait()
        
        return result_container.get("data")

    def _on_screenshot_requested(self, context):
        """处理跨线程截图请求 (在主线程执行)"""
        result_container, event = context
        try:
            result_container["data"] = self._capture_screenshot_impl()
        except Exception as e:
            print(f"Screenshot capture error: {e}")
            result_container["data"] = None
        finally:
            event.set()

    def _capture_screenshot_impl(self) -> Any:
        """截图实现逻辑 (必须在主线程执行)
        
        每次截图时同时更新投屏区域，让用户看到 AI 看到的画面
        """
        try:
            from omg_agent.core.agent.device import Screenshot, get_screenshot
            import base64
            
            # [CRITICAL UPDATE for AutoGLM]
            # Prioritize getting the raw video frame directly from PhoneScreen widget.
            # This ensures we get the EXACT phone screen content, not a "screenshot of the UI widget".
            
            # 1. Try Raw Frame (Best for non-embedded or if decoder is active)
            if (hasattr(self.phone_screen, '_current_frame') and 
                self.phone_screen._current_frame is not None):
                
                # _current_frame contains the raw image data
                raw_frame = self.phone_screen._current_frame
                
                # Convert to QImage if necessary
                qimg = None
                if isinstance(raw_frame, QImage):
                    qimg = raw_frame
                elif isinstance(raw_frame, QPixmap):
                    qimg = raw_frame.toImage()
                elif isinstance(raw_frame, bytes):
                    qimg = QImage.fromData(raw_frame)
                    
                if qimg and not qimg.isNull():
                    ba = QByteArray()
                    buffer = QBuffer(ba)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    qimg.save(buffer, "PNG")
                    base64_data = str(ba.toBase64().data(), 'utf-8')
                    return Screenshot(base64_data, qimg.width(), qimg.height())

            # 2. Use ADB to capture screenshot
            if self.current_device:
                screenshot = get_screenshot(self.current_device)
                
                if screenshot:
                    # 同时更新投屏区域显示，让用户看到 AI 看到的画面
                    try:
                        img_data = base64.b64decode(screenshot.base64_data)
                        self.phone_screen.update_frame(img_data)
                    except Exception as e:
                        print(f"Display update error: {e}")
                
                return screenshot
                
        except Exception as e:
            print(f"Screenshot capture error: {e}")
            import traceback
            traceback.print_exc()
            
        return None

    # === 任务 ===

    def _on_quick_task(self, task: str) -> None:
        s = self._s
        if task and task != s.select_preset:
            self.task_input.setText(task)

    def _start_task(self) -> None:
        s = self._s
        task = self.task_input.text().strip()
        if not task:
            QMessageBox.warning(self, s.notice, s.please_enter_task)
            return

        if not self.current_device:
            QMessageBox.warning(self, s.notice, s.please_connect_device)
            return

        self.thinking_view.clear()
        self._log(s.log_start_task.format(task))

        config = {
            **self.model_config,
            "device_id": self.current_device,
        }

        self.agent_thread = AgentThread(
            task, 
            config, 
            screenshot_provider=self._get_screenshot_from_ui
        )
        self.agent_thread.thinking.connect(self._on_thinking)
        self.agent_thread.action.connect(self._on_action)
        self.agent_thread.step_done.connect(self._on_step)
        self.agent_thread.task_finished.connect(self._on_finished)
        self.agent_thread.finished.connect(self._on_thread_finished)
        self.agent_thread.error.connect(self._on_error)
        self.agent_thread.log.connect(self._log)
        self.agent_thread.start()

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.task_input.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._is_paused = False
        self.status_indicator.set_status("running", s.status_running)

    def _toggle_pause(self) -> None:
        s = self._s
        if not self.agent_thread:
            return

        self._is_paused = not self._is_paused
        if self._is_paused:
            self.agent_thread.pause()
            self.btn_pause.setText(s.resume)
            self._log(s.log_task_paused)
            self.status_indicator.set_status("connecting", s.task_paused)
        else:
            self.agent_thread.resume()
            self.btn_pause.setText(s.pause)
            self._log(s.log_task_resumed)
            self.status_indicator.set_status("running", s.status_running)

    def _stop_task(self) -> None:
        s = self._s
        if self.agent_thread:
            self.agent_thread.stop()
            self._log(s.log_stopping)

    def _on_thinking(self, text: str) -> None:
        s = self._s
        html = f"""
        <div style="background:#1c2128; border-left:2px solid #58a6ff;
                    margin:6px 0; padding:8px 10px;">
            <div style="color:#58a6ff; font-size:10px; margin-bottom:4px;">{s.thinking}</div>
            <div style="color:#c9d1d9; font-size:12px; white-space: pre-wrap;">{text}</div>
        </div>
        """
        self.thinking_view.append(html)
        # Also log to Log tab as requested
        self._log(f"[Thinking] {text[:100]}..." if len(text) > 100 else f"[Thinking] {text}")

    def _on_action(self, text: str) -> None:
        s = self._s
        
        # Try to parse action JSON to extract details for better display
        action_data = {}
        try:
            action_data = json.loads(text)
        except:
            action_data = {"action_type": "UNKNOWN", "params": {}}

        action_type = action_data.get("action_type", "UNKNOWN")
        explanation = action_data.get("explanation", "")
        params = action_data.get("params", {})
        msg = params.get("return", "")
        
        # Build nice HTML display
        content_html = f"<b>Action:</b> {action_type}<br>"
        if explanation:
            content_html += f"<b>Reply:</b> {explanation}<br>"
        if msg:
            content_html += f"<b>Message:</b> {msg}<br>"
            
        # raw params for technical details
        param_str = json.dumps(params, ensure_ascii=False)
        content_html += f"<div style='color:#666; font-size:10px; margin-top:4px'>{param_str}</div>"

        html = f"""
        <div style="background:#0d2818; border-left:2px solid #3fb950;
                    margin:6px 0; padding:8px 10px;">
            <div style="color:#3fb950; font-size:10px; margin-bottom:4px;">{s.execute}</div>
            <div style="color:#7ee787; font-size:11px; font-family:Consolas;">{content_html}</div>
        </div>
        """
        self.thinking_view.append(html)
        
        # Log to log view
        log_msg = f"[Action] {action_type}"
        if explanation:
            log_msg += f" | Reply: {explanation}"
        self._log(log_msg)

    def _on_step(self, step: int, success: bool) -> None:
        s = self._s
        status = s.step_done if success else s.step_warn
        self._log(s.log_step.format(step, status))

    def _on_finished(self, msg: str) -> None:
        s = self._s
        self._reset_task_ui()
        self.status_indicator.set_status("connected", s.status_task_done)
        self._log(s.log_done.format(msg))
        
        # Also show finished message in thinking view
        html = f"""
        <div style="background:#21262d; border:1px solid #30363d; border-radius:6px;
                    margin:10px 0; padding:10px; text-align:center;">
            <div style="color:#c9d1d9; font-weight:bold;">Task Finished</div>
            <div style="color:#8b949e; font-size:12px; margin-top:4px;">{msg}</div>
        </div>
        """
        self.thinking_view.append(html)

        # Add to history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_entry = f"[{timestamp}]\nTask: {self.task_input.text()}\nResult: {msg}\n{'-'*40}\n"
        self.history_view.append(history_entry)
        self._task_history.append(history_entry)

    def _on_error(self, error: str) -> None:
        s = self._s
        self._reset_task_ui()
        self.status_indicator.set_status("error", s.status_task_error)
        self._log(s.log_error.format(error))
        
        # Show error in thinking view
        html = f"""
        <div style="background:#3e1515; border-left:2px solid #f85149;
                    margin:6px 0; padding:8px 10px;">
            <div style="color:#f85149; font-weight:bold; font-size:12px;">Error</div>
            <div style="color:#ffdce0; font-size:11px;">{error}</div>
        </div>
        """
        self.thinking_view.append(html)
        QMessageBox.critical(self, s.error, error[:500])

    def _reset_task_ui(self) -> None:
        s = self._s
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText(s.pause)
        self.btn_stop.setEnabled(False)
        self.task_input.setEnabled(True)
        self.progress.setVisible(False)
        self._is_paused = False

    def _on_thread_finished(self) -> None:
        """Clean up thread reference when it's truly finished (QA safe)"""
        self.agent_thread = None

    # === 辅助 ===

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{ts}] {msg}")

    def _clear_output(self) -> None:
        current_index = self.output_tabs.currentIndex()
        if current_index == 0:
            self.log_view.clear()
        elif current_index == 1:
            self.thinking_view.clear()
        elif current_index == 2:
            self.history_view.clear()

    # === 历史管理 ===
    
    def _refresh_history_list(self) -> None:
        """刷新历史任务列表"""
        history_mgr = get_history_manager()
        tasks = history_mgr.list_tasks(limit=50)
        
        self.history_list.blockSignals(True)
        self.history_list.clear()
        
        self._history_tasks = tasks  # 保存引用
        
        if not tasks:
            self.history_list.addItem("暂无历史记录")
            self.history_view.clear()
        else:
            for task in tasks:
                status_icon = {
                    "completed": "✅",
                    "failed": "❌",
                    "aborted": "⏹️",
                    "running": "🔄",
                }.get(task.status, "❓")
                
                display_text = f"{status_icon} [{task.get_display_time()}] {task.task_name[:30]}"
                self.history_list.addItem(display_text)
        
        self.history_list.blockSignals(False)
        
        # 自动选中第一个
        if tasks:
            self._show_task_detail(tasks[0])
    
    def _on_history_select(self, index: int) -> None:
        """选择历史任务"""
        if hasattr(self, '_history_tasks') and 0 <= index < len(self._history_tasks):
            task = self._history_tasks[index]
            self._show_task_detail(task)
    
    def _show_task_detail(self, task: TaskRecord) -> None:
        """显示任务详情"""
        status_text = {
            "completed": "✅ 已完成",
            "failed": "❌ 失败",
            "aborted": "⏹️ 已中止",
            "running": "🔄 进行中",
        }.get(task.status, task.status)
        
        html = f"""
        <div style="margin-bottom:12px;">
            <div style="font-size:14px; font-weight:bold; color:#58a6ff; margin-bottom:8px;">
                📋 {task.task_name}
            </div>
            <div style="color:#8b949e; font-size:11px; margin-bottom:4px;">
                🕐 开始: {task.get_display_time()} | ⏱️ 耗时: {task.get_duration()} | 状态: {status_text}
            </div>
            <div style="color:#8b949e; font-size:11px;">
                📱 设备: {task.device_id} | 步骤数: {task.total_steps}
            </div>
        </div>
        """
        
        if task.result_summary:
            html += f"""
            <div style="background:#1c2128; border-left:3px solid #3fb950; padding:8px; margin:8px 0;">
                <div style="color:#3fb950; font-size:11px; font-weight:bold;">结果</div>
                <div style="color:#c9d1d9; font-size:12px;">{task.result_summary}</div>
            </div>
            """
        
        html += "<div style='margin-top:12px; color:#58a6ff; font-size:12px; font-weight:bold;'>执行步骤:</div>"
        
        if task.steps:
            for step in task.steps:
                step_num = step.get("step_num", 0)
                action_type = step.get("action_type", "unknown")
                thinking = step.get("thinking", "")[:200]
                result = step.get("result", "")
                success = step.get("success", True)
                
                icon = "✓" if success else "✗"
                color = "#3fb950" if success else "#f85149"
                
                html += f"""
                <div style="background:#21262d; border-radius:4px; padding:8px; margin:4px 0;">
                    <div style="color:{color}; font-size:11px; font-weight:bold;">
                        {icon} 步骤 {step_num}: {action_type}
                    </div>
                """
                
                if thinking:
                    html += f"""
                    <div style="color:#8b949e; font-size:10px; margin-top:4px;">
                        💭 {thinking}...
                    </div>
                    """
                
                if result:
                    html += f"""
                    <div style="color:#c9d1d9; font-size:10px; margin-top:2px;">
                        📝 {result}
                    </div>
                    """
                
                html += "</div>"
        else:
            html += "<div style='color:#8b949e; font-size:11px;'>无步骤记录</div>"
        
        self.history_view.setHtml(html)
    
    def _delete_current_history(self) -> None:
        """删除当前选中的历史记录"""
        index = self.history_list.currentIndex()
        if not hasattr(self, '_history_tasks') or index < 0 or index >= len(self._history_tasks):
            return
        
        task = self._history_tasks[index]
        
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除任务 '{task.task_name}' 的历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            history_mgr = get_history_manager()
            history_mgr.delete_task(task.task_id)
            self._refresh_history_list()
    
    def _clear_all_history(self) -> None:
        """清空所有历史记录"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有历史记录吗？此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            history_mgr = get_history_manager()
            count = history_mgr.clear_all()
            self._refresh_history_list()
            QMessageBox.information(self, "完成", f"已清空 {count} 条历史记录")

    def _set_theme(self, theme: ThemeName) -> None:
        if theme == self._current_theme:
            return
        self._current_theme = theme
        self._dark_action.setChecked(theme == "dark")
        self._light_action.setChecked(theme == "light")
        self._apply_theme()
        # 自动保存配置
        self._save_config()

    def _set_language(self, lang: LanguageCode) -> None:
        if lang == self._current_lang:
            return
        self._current_lang = lang
        I18n.set_language(lang)
        self._zh_action.setChecked(lang == "zh")
        self._en_action.setChecked(lang == "en")
        # 重建菜单以应用新语言
        self.menuBar().clear()
        self._create_menu()
        # 更新所有 UI 元素
        self._update_ui_language()
        # 自动保存配置
        self._save_config()

    def _update_ui_language(self) -> None:
        """更新所有 UI 元素的语言"""
        s = self._s
        
        # 更新投屏控制区
        self.screen_group.setTitle(s.screen_control)
        self.btn_refresh.setText(s.refresh)
        self.btn_start_screen.setText(s.start_screen)
        self.btn_stop_screen.setText(s.stop)
        
        # 更新 AI 任务区
        self.task_group.setTitle(s.ai_task)
        self.task_input.setPlaceholderText(s.input_task)
        self.btn_start.setText(s.execute)
        self.btn_stop.setText(s.stop)
        self.btn_clear.setText(s.clear)
        
        # 更新预设任务下拉框（保留当前选中项）
        current_text = self.task_input.text()
        self.quick_combo.clear()
        self.quick_combo.addItems([s.select_preset] + QUICK_TASKS)
        
        # 更新标签页标题
        self.output_tabs.setTabText(0, s.logs)
        self.output_tabs.setTabText(1, s.thinking)
        self.output_tabs.setTabText(2, s.history)
        
        # 更新状态栏
        self.statusbar.showMessage(s.ready)
        
        # 更新手机屏幕占位符（如果没有画面）
        if not self.phone_screen._current_pixmap:
            self.phone_screen.setText(s.await_screen)

    def _show_model_config(self) -> None:
        s = self._s
        # 传递已保存的配置档案
        dialog = ModelConfigDialog(
            self.model_config, 
            self, 
            saved_profiles=self._config.model_profiles
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.model_config = dialog.get_config()
            # 更新已保存的配置档案
            self._config.model_profiles = dialog.get_saved_profiles()
            self._log(s.log_model_updated)
            # 自动保存配置
            self._save_config()

    def _show_about(self) -> None:
        s = I18n.get_strings()
        QMessageBox.about(self, s.about, s.about_text)

    def resizeEvent(self, event) -> None:
        """窗口大小改变事件"""
        super().resizeEvent(event)
        




    def closeEvent(self, event) -> None:
        if self.capture_thread:
            self.capture_thread.stop()
        if self.agent_thread:
            self.agent_thread.stop()
            self.agent_thread.wait()
        save_config(self._config)
        event.accept()


def run_app() -> None:
    """运行应用程序"""
    # Windows 任务栏图标修复
    if sys.platform == "win32":
        import ctypes
        myappid = "safphere.omgagent.gui.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("OMG-Agent")
    app.setFont(QFont("Microsoft YaHei", 10))

    # 设置应用图标
    logo_path = ASSETS_PATH / "logo.png"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

        # 启动画面
        splash_pixmap = QPixmap(str(logo_path))
        if splash_pixmap.width() > 400:
            splash_pixmap = splash_pixmap.scaledToWidth(
                400, Qt.TransformationMode.SmoothTransformation
            )
        splash = QSplashScreen(splash_pixmap)
        splash.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
        )
        splash.show()
        app.processEvents()

        window = EnhancedMainWindow()

        def show_main_window():
            splash.close()
            window.show()

        QTimer.singleShot(1500, show_main_window)
    else:
        window = EnhancedMainWindow()
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
