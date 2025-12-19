# 开发指南

<p align="center">
  <a href="development.md">English</a> | <a href="development_zh.md">中文</a>
</p>

## 环境搭建

```bash
# 克隆仓库
git clone https://github.com/safphere/OMG-Agent.git
cd OMG-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 项目结构

```
OMG-Agent/
├── omg_agent/
│   ├── __init__.py
│   ├── __main__.py          # 入口点
│   ├── gui/
│   │   ├── main_window.py   # 主窗口
│   │   ├── widgets.py       # 自定义组件
│   │   └── themes.py        # 主题样式
│   └── core/
│       ├── agent/           # AI Agent 核心
│       │   ├── phone_agent.py    # 主 Agent 类
│       │   ├── actions/          # 动作空间
│       │   │   ├── space.py      # 动作定义
│       │   │   ├── parser.py     # 解析器
│       │   │   └── handler.py    # 执行器
│       │   ├── device/           # 设备交互
│       │   │   ├── screenshot.py # 截图
│       │   │   └── apps.py       # 应用映射
│       │   ├── llm/              # LLM 客户端
│       │   │   ├── client.py     # API 客户端
│       │   │   └── message.py    # 消息构建
│       │   ├── prompts/          # 提示词
│       │   ├── history.py        # 历史管理
│       │   └── session.py        # 会话管理
│       ├── config.py        # 配置管理
│       ├── i18n.py          # 国际化
├── assets/                  # 资源文件
├── docs/                    # 文档
├── tests/                   # 测试
└── run.py                   # 启动脚本
```

## 核心模块

### PhoneAgent

主 Agent 类，负责任务执行循环：

```python
from omg_agent.core.agent import PhoneAgent, AgentConfig
from omg_agent.core.agent.llm import LLMConfig

# 配置
llm_config = LLMConfig(
    api_base="http://localhost:8000/v1",
    model="autoglm-phone-9b"
)

agent_config = AgentConfig(
    device_id="emulator-5554",
    max_steps=100
)

# 创建 Agent
agent = PhoneAgent(llm_config, agent_config)

# 执行任务
result = agent.run("打开微信")
print(result.message)
```

### ActionSpace

13 种动作类型：

- `CLICK` - 点击
- `DOUBLE_TAP` - 双击
- `LONG_PRESS` - 长按
- `SWIPE` - 滑动
- `TYPE` - 输入
- `BACK` - 返回
- `HOME` - 主页
- `LAUNCH` - 启动应用
- `WAIT` - 等待
- `INFO` - 询问用户
- `COMPLETE` - 完成
- `ABORT` - 中止
- `TAKE_OVER` - 请求接管

### LLMClient

OpenAI 兼容的 LLM 客户端：

```python
from omg_agent.core.agent.llm import LLMClient, LLMConfig

client = LLMClient(LLMConfig(
    api_base="http://localhost:8000/v1",
    model="autoglm-phone-9b"
))

response = client.request([
    {"role": "user", "content": "Hello"}
])
print(response.content)
```

## 代码规范

```bash
# 格式化
black omg_agent/
isort omg_agent/

# 类型检查
mypy omg_agent/

# 代码检查
ruff check omg_agent/
```

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent.py

# 覆盖率
pytest --cov=omg_agent
```

## 添加新动作

1. 在 `actions/space.py` 添加 ActionType：
```python
class ActionType(str, Enum):
    MY_ACTION = "MY_ACTION"
```

2. 在 `actions/handler.py` 添加处理器：
```python
def _handle_my_action(self, action: Action) -> ActionResult:
    # 实现逻辑
    return ActionResult(success=True, should_finish=False)
```

3. 更新 `REQUIRED_PARAMS` 和 `OPTIONAL_PARAMS`

## 添加新语言

1. 在 `core/i18n.py` 的 `Strings` 类添加字段
2. 创建新的语言配置（参考 `_CHINESE` 和 `_ENGLISH`）
3. 在 `_LANGUAGES` 字典中注册

## 发布

```bash
# 构建
python -m build

# 上传到 PyPI
twine upload dist/*
```
