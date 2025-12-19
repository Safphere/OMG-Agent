"""
主题定义模块

提供深色和浅色主题的颜色定义
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

ThemeName = Literal["dark", "light"]


@dataclass
class ThemeColors:
    """主题颜色定义"""
    
    # 背景色
    main_bg: str
    panel_bg: str
    input_bg: str
    
    # 边框和分隔线
    border: str
    
    # 文字颜色
    text: str
    text_secondary: str
    
    # 强调色
    accent: str
    success: str
    danger: str
    warning: str
    
    # 按钮颜色
    button_bg: str
    button_hover: str


# 主题定义
THEMES: Dict[ThemeName, ThemeColors] = {
    "dark": ThemeColors(
        main_bg="#0d1117",
        panel_bg="#161b22",
        input_bg="#0d1117",
        border="#30363d",
        text="#c9d1d9",
        text_secondary="#8b949e",
        accent="#58a6ff",
        success="#3fb950",
        danger="#f85149",
        warning="#d29922",
        button_bg="#21262d",
        button_hover="#30363d",
    ),
    "light": ThemeColors(
        main_bg="#ffffff",
        panel_bg="#f6f8fa",
        input_bg="#ffffff",
        border="#d0d7de",
        text="#24292f",
        text_secondary="#57606a",
        accent="#0969da",
        success="#1a7f37",
        danger="#cf222e",
        warning="#9a6700",
        button_bg="#f6f8fa",
        button_hover="#eaeef2",
    ),
}


def get_theme(name: ThemeName) -> ThemeColors:
    """获取主题颜色"""
    return THEMES.get(name, THEMES["dark"])


def generate_stylesheet(theme: ThemeColors) -> str:
    """生成 Qt 样式表"""
    return f"""
        QMainWindow {{
            background-color: {theme.main_bg};
        }}
        
        QGroupBox {{
            font-weight: 600;
            font-size: 13px;
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 8px;
            background-color: {theme.panel_bg};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            background-color: {theme.panel_bg};
        }}
        
        QPushButton {{
            background-color: {theme.button_bg};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {theme.button_hover};
            border-color: {theme.accent};
        }}
        
        QPushButton:pressed {{
            background-color: {theme.main_bg};
            border-color: {theme.accent};
        }}
        
        QPushButton:disabled {{
            background-color: {theme.main_bg};
            color: {theme.text_secondary};
            border-color: {theme.border};
        }}
        
        QPushButton#primary {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #60a5fa, stop:1 #3b82f6);
            border: none;
            border-radius: 6px;
            color: #ffffff;
            font-weight: 500;
            padding: 8px 18px;
        }}

        QPushButton#primary:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #93c5fd, stop:1 #60a5fa);
        }}

        QPushButton#primary:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2563eb, stop:1 #1d4ed8);
        }}

        QPushButton#danger {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #9ca3af, stop:1 #6b7280);
            border: none;
            border-radius: 6px;
            color: #ffffff;
            font-weight: 500;
            padding: 8px 18px;
        }}

        QPushButton#danger:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f87171, stop:1 #ef4444);
        }}

        QPushButton#danger:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #dc2626, stop:1 #b91c1c);
        }}

        QPushButton#primary:disabled, QPushButton#danger:disabled {{
            background: #374151;
            color: #6b7280;
        }}

        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {theme.input_bg};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
            selection-background-color: {theme.accent};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {theme.accent};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {theme.text_secondary};
            margin-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme.panel_bg};
            color: {theme.text};
            selection-background-color: {theme.accent};
            border: 1px solid {theme.border};
            border-radius: 6px;
        }}
        
        QLabel {{
            color: {theme.text};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {theme.border};
            border-radius: 6px;
            background-color: {theme.main_bg};
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            color: {theme.text_secondary};
            padding: 8px 16px;
            border: 1px solid transparent;
            border-bottom: none;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme.main_bg};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-bottom: 1px solid {theme.main_bg};
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QScrollBar:vertical {{
            background-color: {theme.main_bg};
            width: 8px;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme.border};
            border-radius: 4px;
            min-height: 24px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme.text_secondary};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QProgressBar {{
            background-color: {theme.button_bg};
            border: none;
            border-radius: 3px;
        }}
        
        QProgressBar::chunk {{
            background-color: {theme.accent};
            border-radius: 3px;
        }}
        
        QDialog {{
            background-color: {theme.main_bg};
        }}
        
        QStatusBar {{
            background-color: {theme.panel_bg};
            color: {theme.text_secondary};
            border-top: 1px solid {theme.border};
        }}
        
        QMenuBar {{
            background-color: {theme.panel_bg};
            color: {theme.text};
            border-bottom: 1px solid {theme.border};
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme.button_hover};
        }}
        
        QMenu {{
            background-color: {theme.panel_bg};
            color: {theme.text};
            border: 1px solid {theme.border};
        }}
        
        QMenu::item:selected {{
            background-color: {theme.accent};
        }}
    """
