"""
多语言支持模块 (i18n - Internationalization)

提供中英双语支持
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

LanguageCode = Literal["zh", "en"]


@dataclass
class Strings:
    """语言字符串集合"""
    
    # 应用信息
    app_name: str
    about_text: str
    
    # 菜单
    file: str
    model_config: str
    exit: str
    device: str
    refresh_devices: str
    wireless_connect: str
    disconnect_all: str
    view: str
    theme: str
    dark_theme: str
    light_theme: str
    language: str
    help: str
    about: str
    
    # 投屏控制
    screen_control: str
    refresh: str
    start_screen: str
    stop: str
    
    # AI 任务
    ai_task: str
    select_preset: str
    input_task: str
    execute: str
    
    # 输出标签页
    thinking: str
    logs: str
    history: str
    clear: str
    
    # 状态
    ready: str
    no_device: str
    connected: str
    task_start: str
    task_done: str
    task_error: str
    step_done: str
    step_warn: str
    
    # 对话框
    confirm_clear: str
    confirm_clear_history: str
    notice: str
    error: str
    connect_failed: str
    
    # 日志消息
    log_found_devices: str
    log_no_device: str
    log_switch_device: str
    log_refresh_failed: str
    log_adb_error: str
    log_tap: str
    log_swipe: str
    log_back: str
    log_home: str
    log_recent: str
    log_swipe_up: str
    log_swipe_down: str
    log_swipe_left: str
    log_swipe_right: str
    log_connecting: str
    log_connected: str
    log_connect_failed: str
    log_connect_error: str
    log_disconnected_all: str
    log_disconnect_failed: str
    log_start_screen: str
    log_stop_screen: str
    log_screen_error: str
    log_start_task: str
    log_stopping: str
    log_step: str
    log_done: str
    log_error: str
    log_model_updated: str
    log_adb_failed: str
    log_task_stopped: str
    log_task_done: str
    
    # 状态指示器
    status_connected: str
    status_disconnected: str
    status_screening: str
    status_screen_stopped: str
    status_running: str
    status_task_done: str
    status_task_error: str
    
    # 无线连接对话框
    wireless_title: str
    wireless_info: str
    wireless_ip: str
    wireless_port: str
    wireless_quick: str
    wireless_enable_tcpip: str
    wireless_tcpip_ok: str
    wireless_tcpip_fail: str
    wireless_enter_ip: str
    cannot_connect: str
    
    # 模型配置对话框
    model_preset: str
    model_detail: str
    model_url: str
    model_key: str
    model_name: str
    model_advanced: str
    model_temperature: str
    model_max_tokens: str
    model_step_delay: str
    model_auto_wake: str
    model_reset_home: str

    # 任务控制
    pause: str
    resume: str
    task_paused: str
    log_task_paused: str
    log_task_resumed: str
    

    
    # 其他
    please_connect_device: str
    please_enter_task: str
    await_screen: str


# 语言定义
LANGUAGES: Dict[LanguageCode, Strings] = {
    "zh": Strings(
        app_name="OMG-Agent",
        about_text="<h3>OMG-Agent</h3>"
                   "<p>Open-sourced Mobile GUI Agent</p>"
                   "<p>开源、免费的移动端 GUI Agent 框架</p>"
                   "<p><b>Version:</b> 1.0.0</p>"
                   "<p><b>Powered by:</b> Safphere</p>"
                   "<p>Safphere 是由算法工程师与高校极客组成的开源社区，</p>"
                   "<p>专注于 AI+ 领域的技术探索与知识分享。</p>"
                   "<p>🌐 <a href='https://github.com/safphere'>github.com/safphere</a></p>"
                   "<p>© 2025 Safphere | Made with ❤️ by mrcat</p>",
        file="文件",
        model_config="模型配置",
        exit="退出",
        device="设备",
        refresh_devices="刷新设备",
        wireless_connect="无线连接...",
        disconnect_all="断开所有无线设备",
        view="视图",
        theme="主题",
        dark_theme="深色",
        light_theme="浅色",
        language="语言",
        help="帮助",
        about="关于",
        screen_control="投屏控制",
        refresh="刷新",
        start_screen="开始投屏",
        stop="停止",
        ai_task="AI 任务",
        select_preset="选择预设任务...",
        input_task="输入任务指令...",
        execute="执行任务",
        thinking="思考",
        logs="日志",
        history="历史",
        clear="清空",
        ready="就绪",
        no_device="未发现设备",
        connected="已连接",
        task_start="任务开始",
        task_done="任务完成",
        task_error="任务出错",
        step_done="完成",
        step_warn="警告",
        confirm_clear="确认清空",
        confirm_clear_history="确定要清空所有任务历史记录吗？",
        notice="提示",
        error="错误",
        connect_failed="连接失败",
        # 日志消息
        log_found_devices="发现 {} 个设备",
        log_no_device="未发现设备",
        log_switch_device="切换设备: {}",
        log_refresh_failed="刷新设备失败: {}",
        log_adb_error="ADB 错误",
        log_tap="点击 ({}, {})",
        log_swipe="滑动 ({},{}) → ({},{})",
        log_back="返回",
        log_home="主屏",
        log_recent="最近任务",
        log_swipe_up="上滑",
        log_swipe_down="下滑",
        log_swipe_left="左滑",
        log_swipe_right="右滑",
        log_connecting="正在连接 {}...",
        log_connected="✓ 已连接到 {}",
        log_connect_failed="✗ 连接失败: {}",
        log_connect_error="✗ 连接错误: {}",
        log_disconnected_all="已断开所有无线设备",
        log_disconnect_failed="断开失败: {}",
        log_start_screen="开始投屏",
        log_stop_screen="停止投屏",
        log_screen_error="截图错误: {}",
        log_start_task="开始任务: {}",
        log_stopping="正在停止...",
        log_step="步骤 {} {}",
        log_done="完成: {}",
        log_error="错误: {}",
        log_model_updated="模型配置已更新",
        log_adb_failed="ADB 命令失败: {}",
        log_task_stopped="任务已停止",
        log_task_done="任务完成",
        # 状态指示器
        status_connected="已连接: {}",
        status_disconnected="未连接",
        status_screening="投屏中",
        status_screen_stopped="投屏已停止",
        status_running="执行中...",
        status_task_done="任务完成",
        status_task_error="任务出错",
        # 无线连接对话框
        wireless_title="无线连接设备",
        wireless_info="请确保手机与电脑在同一局域网内，\n并且手机已开启 USB 调试和无线调试。",
        wireless_ip="IP 地址:",
        wireless_port="端口:",
        wireless_quick="快捷操作",
        wireless_enable_tcpip="启用 TCP/IP 模式 (需先 USB 连接)",
        wireless_tcpip_ok="✓ TCP/IP 模式已启用，请断开 USB 后连接",
        wireless_tcpip_fail="✗ 启用失败: {}",
        wireless_enter_ip="请输入 IP 地址",
        cannot_connect="无法连接到 {}",
        # 模型配置对话框
        model_preset="预设配置",
        model_detail="基本配置",
        model_url="API Base URL:",
        model_key="API Key:",
        model_name="模型名称:",
        model_advanced="高级设置",
        model_temperature="Temperature:",
        model_max_tokens="Max Tokens:",
        model_step_delay="步骤延迟 (秒):",
        model_auto_wake="自动唤醒屏幕",
        model_reset_home="执行前返回主屏",
        # 任务控制
        pause="暂停",
        resume="继续",
        task_paused="任务已暂停",
        log_task_paused="任务已暂停",
        log_task_resumed="任务已继续",

        # 其他
        please_connect_device="请先连接设备",
        please_enter_task="请输入任务",
        await_screen="📱 等待投屏...",
    ),
    "en": Strings(
        app_name="OMG-Agent",
        about_text="<h3>OMG-Agent</h3>"
                   "<p>Open-sourced Mobile GUI Agent</p>"
                   "<p>Free and open-source Mobile GUI Agent framework</p>"
                   "<p><b>Version:</b> 1.0.0</p>"
                   "<p><b>Powered by:</b> Safphere</p>"
                   "<p>Safphere is an open-source community of AI engineers</p>"
                   "<p>and university geeks, exploring AI+ technologies.</p>"
                   "<p>🌐 <a href='https://github.com/safphere'>github.com/safphere</a></p>"
                   "<p>© 2025 Safphere | Made with ❤️ by mrcat</p>",
        file="File",
        model_config="Model Config",
        exit="Exit",
        device="Device",
        refresh_devices="Refresh Devices",
        wireless_connect="Wireless Connect...",
        disconnect_all="Disconnect All Wireless",
        view="View",
        theme="Theme",
        dark_theme="Dark",
        light_theme="Light",
        language="Language",
        help="Help",
        about="About",
        screen_control="Screen Control",
        refresh="Refresh",
        start_screen="Start",
        stop="Stop",
        ai_task="AI Task",
        select_preset="Select preset task...",
        input_task="Enter task instruction...",
        execute="Execute",
        thinking="Thinking",
        logs="Logs",
        history="History",
        clear="Clear",
        ready="Ready",
        no_device="No device found",
        connected="Connected",
        task_start="Task started",
        task_done="Task completed",
        task_error="Task error",
        step_done="done",
        step_warn="warning",
        confirm_clear="Confirm Clear",
        confirm_clear_history="Are you sure to clear all task history?",
        notice="Notice",
        error="Error",
        connect_failed="Connection Failed",
        # Log messages
        log_found_devices="Found {} device(s)",
        log_no_device="No device found",
        log_switch_device="Switched to: {}",
        log_refresh_failed="Refresh failed: {}",
        log_adb_error="ADB Error",
        log_tap="Tap ({}, {})",
        log_swipe="Swipe ({},{}) → ({},{})",
        log_back="Back",
        log_home="Home",
        log_recent="Recent",
        log_swipe_up="Swipe Up",
        log_swipe_down="Swipe Down",
        log_swipe_left="Swipe Left",
        log_swipe_right="Swipe Right",
        log_connecting="Connecting to {}...",
        log_connected="✓ Connected to {}",
        log_connect_failed="✗ Connection failed: {}",
        log_connect_error="✗ Connection error: {}",
        log_disconnected_all="Disconnected all wireless devices",
        log_disconnect_failed="Disconnect failed: {}",
        log_start_screen="Screen started",
        log_stop_screen="Screen stopped",
        log_screen_error="Screenshot error: {}",
        log_start_task="Starting task: {}",
        log_stopping="Stopping...",
        log_step="Step {} {}",
        log_done="Done: {}",
        log_error="Error: {}",
        log_model_updated="Model config updated",
        log_adb_failed="ADB command failed: {}",
        log_task_stopped="Task stopped",
        log_task_done="Task completed",
        # Status indicator
        status_connected="Connected: {}",
        status_disconnected="Disconnected",
        status_screening="Streaming",
        status_screen_stopped="Stream stopped",
        status_running="Running...",
        status_task_done="Task completed",
        status_task_error="Task error",
        # Wireless connect dialog
        wireless_title="Wireless Connect",
        wireless_info="Ensure phone and computer are on the same LAN,\nand USB debugging and wireless debugging are enabled.",
        wireless_ip="IP Address:",
        wireless_port="Port:",
        wireless_quick="Quick Actions",
        wireless_enable_tcpip="Enable TCP/IP Mode (USB connection required)",
        wireless_tcpip_ok="✓ TCP/IP mode enabled, disconnect USB and connect",
        wireless_tcpip_fail="✗ Enable failed: {}",
        wireless_enter_ip="Please enter IP address",
        cannot_connect="Cannot connect to {}",
        # Model config dialog
        model_preset="Preset Config",
        model_detail="Basic Config",
        model_url="API Base URL:",
        model_key="API Key:",
        model_name="Model Name:",
        model_advanced="Advanced Settings",
        model_temperature="Temperature:",
        model_max_tokens="Max Tokens:",
        model_step_delay="Step Delay (sec):",
        model_auto_wake="Auto Wake Screen",
        model_reset_home="Reset to Home Before Task",
        # Task control
        pause="Pause",
        resume="Resume",
        task_paused="Task Paused",
        log_task_paused="Task paused",
        log_task_resumed="Task resumed",

        # Other
        please_connect_device="Please connect a device first",
        please_enter_task="Please enter a task",
        await_screen="📱 Awaiting screen...",
    ),
}


class I18n:
    """国际化管理器"""
    
    _current_lang: LanguageCode = "zh"
    
    @classmethod
    def set_language(cls, lang: LanguageCode) -> None:
        """设置当前语言"""
        if lang in LANGUAGES:
            cls._current_lang = lang
    
    @classmethod
    def get_language(cls) -> LanguageCode:
        """获取当前语言"""
        return cls._current_lang
    
    @classmethod
    def get_strings(cls) -> Strings:
        """获取当前语言的字符串集合"""
        return LANGUAGES[cls._current_lang]


def get_text(key: str) -> str:
    """获取本地化文本的快捷函数"""
    strings = I18n.get_strings()
    return getattr(strings, key, key)
