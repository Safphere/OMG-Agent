"""
配置管理模块

提供应用配置的加载、保存和管理功能
支持多模型配置保存，记录当前使用的模型
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# 默认配置目录
CONFIG_DIR = Path.home() / ".omg-agent" / "configs"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 历史记录目录
HISTORY_DIR = Path.home() / ".omg-agent" / "history"


@dataclass
class ModelProfile:
    """模型配置档案"""
    
    name: str = "自定义"
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_steps: int = 30
    temperature: float = 0.7
    max_tokens: int = 4096
    step_delay: float = 1.0
    auto_wake: bool = True
    reset_home: bool = True


# 兼容旧版本
ModelConfig = ModelProfile


@dataclass
class UIConfig:
    """界面配置"""
    
    theme: str = "dark"
    language: str = "zh"
    window_width: int = 1280
    window_height: int = 800


@dataclass
class Config:
    """应用配置"""
    
    # 当前使用的模型配置
    current_profile: str = "自定义"
    
    # 所有保存的模型配置 (name -> ModelProfile)
    model_profiles: dict = field(default_factory=dict)
    
    # UI 配置
    ui: UIConfig = field(default_factory=UIConfig)
    
    # 上次使用的设备
    last_device: Optional[str] = None
    
    def __post_init__(self):
        """确保当前配置存在"""
        if not self.model_profiles:
            self.model_profiles = {"自定义": asdict(ModelProfile())}
        if self.current_profile not in self.model_profiles:
            self.current_profile = list(self.model_profiles.keys())[0]
    
    @property
    def model(self) -> ModelProfile:
        """获取当前模型配置"""
        profile_dict = self.model_profiles.get(self.current_profile, {})
        fields = {f.name for f in ModelProfile.__dataclass_fields__.values()}
        filtered = {k: v for k, v in profile_dict.items() if k in fields}
        return ModelProfile(**filtered)
    
    def set_model(self, profile: ModelProfile) -> None:
        """设置当前模型配置"""
        self.model_profiles[profile.name] = asdict(profile)
        self.current_profile = profile.name
    
    def get_profile_names(self) -> list[str]:
        """获取所有配置档案名称"""
        return list(self.model_profiles.keys())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "current_profile": self.current_profile,
            "model_profiles": self.model_profiles,
            "ui": asdict(self.ui),
            "last_device": self.last_device,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Config:
        """从字典创建配置"""
        ui_data = data.get("ui", {})
        ui_fields = {f.name for f in UIConfig.__dataclass_fields__.values()}
        
        # 兼容旧版本配置（只有单个 model 字段）
        model_profiles = data.get("model_profiles", {})
        if not model_profiles and "model" in data:
            old_model = data["model"]
            old_model["name"] = "自定义"
            model_profiles = {"自定义": old_model}
        
        return cls(
            current_profile=data.get("current_profile", "自定义"),
            model_profiles=model_profiles,
            ui=UIConfig(**{k: v for k, v in ui_data.items() if k in ui_fields}),
            last_device=data.get("last_device"),
        )


def load_config() -> Config:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Config.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load config: {e}")
    return Config()


def save_config(config: Config) -> None:
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


# 模型预设 (内置模板，不保存 API Key)
MODEL_PRESETS = {
    "自定义": ModelProfile(name="自定义"),
    "Step (阶跃星辰)": ModelProfile(
        name="Step (阶跃星辰)",
        base_url="https://api.stepfun.com/v1",
        api_key="",
        model_name="step-gui",
    ),
    "BigModel (智谱)": ModelProfile(
        name="BigModel (智谱)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="",
        model_name="ZhipuAI/AutoGLM-Phone-9B",
    ),
    "魔搭 ModelScope": ModelProfile(
        name="魔搭 ModelScope",
        base_url="https://api-inference.modelscope.cn/v1",
        api_key="",
        model_name="ZhipuAI/AutoGLM-Phone-9B",
    ),
    "z.ai": ModelProfile(
        name="z.ai",
        base_url="https://api.z.ai/v1",
        api_key="",
        model_name="autoglm-phone-9b",
    ),
}

# 快捷任务预设
QUICK_TASKS = [
    "打开微信",
    "打开设置",
    "截图并保存",
    "返回主屏幕",
    "查看最近通知",
]

# 滑动手势预设
SWIPE_GESTURES = {
    "上滑": {"start": (500, 800), "end": (500, 200)},
    "下滑": {"start": (500, 200), "end": (500, 800)},
    "左滑": {"start": (800, 500), "end": (200, 500)},
    "右滑": {"start": (200, 500), "end": (800, 500)},
}
