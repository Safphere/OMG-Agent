"""
自定义 GUI 组件模块

提供手机屏幕显示、快捷操作栏、状态指示器等组件
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from omg_agent.core.i18n import I18n


class PhoneScreen(QLabel):
    """
    手机屏幕显示组件
    
    支持:
    - 实时显示视频帧
    - 点击事件
    - 滑动手势
    - 长按检测
    """

    # 信号定义
    clicked = pyqtSignal(int, int)           # 单击 (x, y)
    double_clicked = pyqtSignal(int, int)    # 双击 (x, y)
    long_pressed = pyqtSignal(int, int)      # 长按 (x, y)
    swiped = pyqtSignal(int, int, int, int)  # 滑动 (x1, y1, x2, y2)

    # 长按时间阈值（毫秒）
    LONG_PRESS_DURATION = 800
    # 滑动距离阈值（像素）
    SWIPE_THRESHOLD = 30
    
    # 尺寸改变信号
    resized = pyqtSignal(int, int)

    def resizeEvent(self, event) -> None:
        """大小改变事件"""
        super().resizeEvent(event)
        self.resized.emit(event.size().width(), event.size().height())

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_state()
        self._setup_timer()

    def _setup_ui(self) -> None:
        """设置组件样式"""
        self.setMinimumSize(300, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #8b949e;
                font-size: 14px;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }
        """)
        self.setText(I18n.get_strings().await_screen)
        self.setScaledContents(False)

    def _setup_state(self) -> None:
        """初始化状态变量"""
        self._screen_size: Tuple[int, int] = (1080, 1920)
        self._original_pixmap: Optional[QPixmap] = None
        self._current_pixmap: Optional[QPixmap] = None
        self._press_pos: Optional[QPoint] = None
        self._is_long_press: bool = False
        self._show_resolution: bool = True  # 显示分辨率信息

    def _setup_timer(self) -> None:
        """设置长按检测定时器"""
        self._long_press_timer = QTimer()
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press_timeout)

    def update_frame(self, image_data) -> None:
        """
        更新显示帧
        
        Args:
            image_data: QPixmap, QImage 或 bytes 类型的图像数据
        """
        try:
            pixmap = self._convert_to_pixmap(image_data)
            if pixmap is None:
                return

            # 保存原始尺寸（用于坐标转换）
            # 注意：这里保存的是接收到的图像尺寸，即实际设备屏幕尺寸
            self._screen_size = (pixmap.width(), pixmap.height())
            self._original_pixmap = pixmap
            
            # 根据可用空间缩放（仅用于显示）
            scaled_pixmap = self._scale_pixmap(pixmap)
            self._current_pixmap = scaled_pixmap
            
            # Store raw frame for agent screenshot (crucial for AutoGLM)
            # This allows the agent to get the exact phone screen content
            self._current_frame = image_data 
            
            self.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"更新帧失败: {e}")

    def set_screen_size(self, width: int, height: int) -> None:
        """
        设置真实屏幕尺寸（用于坐标转换）
        在某些模式下，接收到的图像可能已被压缩，需要手动设置真实尺寸
        """
        self._screen_size = (width, height)

    def _convert_to_pixmap(self, image_data) -> Optional[QPixmap]:
        """将各种格式的图像数据转换为 QPixmap"""
        if isinstance(image_data, QPixmap):
            return image_data
        elif isinstance(image_data, QImage):
            return QPixmap.fromImage(image_data)
        else:
            # bytes 类型
            image = QImage.fromData(image_data)
            if image.isNull():
                return None
            return QPixmap.fromImage(image)

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """根据可用空间缩放图像（保持纵横比）"""
        available_size = self.size()
        if available_size.width() <= 0 or available_size.height() <= 0:
            return pixmap
            
        scale_x = available_size.width() / pixmap.width()
        scale_y = available_size.height() / pixmap.height()
        scale = min(scale_x, scale_y)  # 允许放大和缩小

        new_width = int(pixmap.width() * scale)
        new_height = int(pixmap.height() * scale)
        
        if new_width > 0 and new_height > 0:
            return pixmap.scaled(
                new_width,
                new_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pixmap

    def _to_screen_coords(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        """将组件坐标转换为屏幕坐标"""
        if not self._current_pixmap:
            return None

        pixmap_rect = self._current_pixmap.rect()
        widget_rect = self.rect()

        # 计算偏移（图像居中显示）
        x_offset = (widget_rect.width() - pixmap_rect.width()) // 2
        y_offset = (widget_rect.height() - pixmap_rect.height()) // 2

        # 相对于图片的位置
        click_x = pos.x() - x_offset
        click_y = pos.y() - y_offset

        # 检查是否在图片范围内
        if 0 <= click_x <= pixmap_rect.width() and 0 <= click_y <= pixmap_rect.height():
            real_x = int(click_x * self._screen_size[0] / pixmap_rect.width())
            real_y = int(click_y * self._screen_size[1] / pixmap_rect.height())
            return (real_x, real_y)

        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._is_long_press = False
            self._long_press_timer.start(self.LONG_PRESS_DURATION)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放事件"""
        self._long_press_timer.stop()

        if event.button() == Qt.MouseButton.LeftButton and self._press_pos:
            release_pos = event.pos()
            dx = abs(release_pos.x() - self._press_pos.x())
            dy = abs(release_pos.y() - self._press_pos.y())

            if self._is_long_press:
                pass  # 长按已处理
            elif dx > self.SWIPE_THRESHOLD or dy > self.SWIPE_THRESHOLD:
                # 滑动手势
                start = self._to_screen_coords(self._press_pos)
                end = self._to_screen_coords(release_pos)
                if start and end:
                    self.swiped.emit(start[0], start[1], end[0], end[1])
            else:
                # 点击
                coords = self._to_screen_coords(release_pos)
                if coords:
                    self.clicked.emit(coords[0], coords[1])

            self._press_pos = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            coords = self._to_screen_coords(event.pos())
            if coords:
                self.double_clicked.emit(coords[0], coords[1])

    def _on_long_press_timeout(self) -> None:
        """长按超时处理"""
        if self._press_pos:
            self._is_long_press = True
            coords = self._to_screen_coords(self._press_pos)
            if coords:
                self.long_pressed.emit(coords[0], coords[1])

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        return self._screen_size


class QuickActionBar(QWidget):
    """
    快捷操作栏
    
    提供方向滑动和导航按钮
    """

    action_triggered = pyqtSignal(str)

    # 按钮样式模板
    _BUTTON_STYLE = """
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {bg_start}, stop:1 {bg_end});
            color: {text_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            padding: 0;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {hover_start}, stop:1 {hover_end});
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {pressed_start}, stop:1 {pressed_end});
            border-color: {accent};
        }}
    """

    # 颜色配置
    _COLORS = {
        "direction": {
            "bg_start": "#2d3748",
            "bg_end": "#1a202c",
            "hover_start": "#4a5568",
            "hover_end": "#2d3748",
            "pressed_start": "#1a202c",
            "pressed_end": "#171923",
            "text_color": "#90cdf4",
            "border_color": "#4a5568",
            "accent": "#63b3ed",
        },
        "nav": {
            "bg_start": "#22543d",
            "bg_end": "#1a3a2a",
            "hover_start": "#2f855a",
            "hover_end": "#22543d",
            "pressed_start": "#1a3a2a",
            "pressed_end": "#153326",
            "text_color": "#9ae6b4",
            "border_color": "#2f855a",
            "accent": "#68d391",
        },
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._buttons: dict = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 按钮配置：(图标, 动作名, 颜色类型)
        actions = [
            ("⬆", "swipe_up", "direction"),
            ("⬇", "swipe_down", "direction"),
            ("⬅", "swipe_left", "direction"),
            ("➡", "swipe_right", "direction"),
            ("🏠", "home", "nav"),
            ("◀", "back", "nav"),
            ("☰", "recent", "nav"),
        ]

        for icon, action, color_type in actions:
            btn = QPushButton(icon)
            btn.setFixedSize(38, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._BUTTON_STYLE.format(**self._COLORS[color_type]))
            btn.clicked.connect(lambda checked, a=action: self.action_triggered.emit(a))
            self._buttons[action] = btn
            layout.addWidget(btn)

        layout.addStretch()


class StatusIndicator(QFrame):
    """
    状态指示器
    
    显示当前连接状态
    """

    # 状态颜色映射
    _STATUS_COLORS = {
        "disconnected": "#888888",
        "connecting": "#ffa500",
        "connected": "#4CAF50",
        "error": "#f44336",
        "running": "#2196F3",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = "disconnected"
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._indicator = QLabel("●")
        self._indicator.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._indicator)

        self._label = QLabel(I18n.get_strings().status_disconnected)
        self._label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._label)

        layout.addStretch()

    def set_status(self, status: str, message: str = "") -> None:
        """
        设置状态
        
        Args:
            status: 状态类型 (disconnected, connecting, connected, error, running)
            message: 显示消息
        """
        self._status = status
        color = self._STATUS_COLORS.get(status, "#888888")
        self._indicator.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._label.setText(message or status)
        self._label.setStyleSheet(f"color: {color}; font-size: 12px;")


class ThinkingBubble(QFrame):
    """思考气泡"""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui(text)

    def _setup_ui(self, text: str) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d44;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        layout.addWidget(label)


class ActionBubble(QFrame):
    """动作气泡"""

    def __init__(self, action: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui(action)

    def _setup_ui(self, action: str) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1a472a;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(f"🎯 {action}")
        label.setWordWrap(True)
        label.setStyleSheet("color: #90EE90; font-size: 13px; font-family: Consolas;")
        layout.addWidget(label)
