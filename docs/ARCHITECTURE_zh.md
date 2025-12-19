# OMG-Agent 完整架构设计文档

> 版本: 1.0 | 更新时间: 2025-12-19

## 一、项目概述

OMG-Agent 是一个基于视觉语言模型(VLM)的手机自动化代理，能够理解自然语言任务描述，通过分析屏幕截图来执行手机操作。

### 核心能力
- 自然语言任务理解
- 屏幕截图视觉分析
- 任务自动规划与分解
- 循环检测与防死锁
- 多模型格式兼容 (AutoGLM / gelab-zero)

---

## 二、架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                         GUI (PyQt6)                                  ││
│  │  • MainWindow - 主窗口                                               ││
│  │  • PhoneScreen - 手机投屏                                            ││
│  │  • TaskInput - 任务输入                                              ││
│  │  • ThinkingView - 推理过程展示                                       ││
│  │  • LogView - 日志显示                                                ││
│  └─────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              核心代理层                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                       PhoneAgent (主控制器)                          ││
│  │  • run() - 完整任务执行                                              ││
│  │  • step() - 单步执行                                                 ││
│  │  • _execute_step() - 核心循环                                        ││
│  │  • _try_advance_subtask() - 子任务进度推进                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│          │                    │                    │                     │
│          ▼                    ▼                    ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐           │
│  │HistoryManager│    │  LLMClient   │    │  ActionHandler   │           │
│  │• 历史管理     │    │• API 调用    │    │• 动作执行        │           │
│  │• 循环检测     │    │• 响应解析    │    │• ADB 命令        │           │
│  │• 任务规划集成 │    │              │    │                  │           │
│  └──────────────┘    └──────────────┘    └──────────────────┘           │
│          │                                         │                     │
│          ▼                                         ▼                     │
│  ┌──────────────┐                         ┌──────────────────┐           │
│  │ TaskPlanner  │                         │  ActionParser    │           │
│  │• 模式匹配     │                         │• 格式自动检测    │           │
│  │• LLM 动态分解 │                         │• 多格式兼容      │           │
│  │• 进度跟踪     │                         │                  │           │
│  └──────────────┘                         └──────────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              设备交互层                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐           │
│  │  截屏模块     │    │  ADB 执行器  │    │   GUI 投屏     │           │
│  │• 屏幕捕获     │    │• tap/swipe   │    │• 实时画面        │           │
│  │• Base64 编码  │    │• type/back   │    │• 触控映射        │           │
│  └──────────────┘    └──────────────┘    └──────────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解

### 3.1 PhoneAgent (`phone_agent.py`) - 675行

**职责**: 主控制器，协调所有组件完成任务

#### 数据结构

```python
@dataclass
class AgentConfig:
    device_id: str | None = None      # ADB 设备 ID
    max_steps: int = 100              # 最大执行步数
    step_delay: float = 1.0           # 步骤间延迟
    lang: str = "zh"                  # 语言 (zh/en)
    system_prompt: str | None = None  # 系统提示词
    reply_mode: ReplyMode = CALLBACK  # INFO 动作处理模式
    auto_wake_screen: bool = True     # 自动唤醒屏幕
    reset_to_home: bool = True        # 任务前返回桌面

@dataclass
class StepResult:
    success: bool                     # 步骤是否成功
    finished: bool                    # 任务是否结束
    action: Action | None             # 执行的动作
    message: str | None               # 结果消息
    needs_user_input: bool = False    # 是否需要用户输入
    step_count: int = 0               # 当前步骤数

@dataclass  
class RunResult:
    success: bool                     # 任务是否成功
    message: str                      # 完成消息
    step_count: int                   # 总步骤数
    stop_reason: str                  # 停止原因
```

#### 核心方法

| 方法 | 功能 | 关键逻辑 |
|------|------|----------|
| `run(task)` | 完整执行任务 | 循环调用 `_execute_step` 直到完成 |
| `step(task)` | 单步执行 | GUI 集成入口 |
| `_execute_step()` | 核心循环 | 截屏→构建上下文→LLM→解析→执行→记录 |
| `_try_advance_subtask()` | 子任务推进 | 根据动作类型判断是否完成当前子任务 |

#### 执行流程 (`_execute_step`)

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 屏幕捕获                                                 │
│ • take_screenshot() → 获取屏幕截图 (base64)                      │
│ • get_current_app() → 获取当前应用包名                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 构建上下文                                               │
│ • history_manager.build_context_messages()                       │
│   - System Message (系统提示词)                                  │
│   - History Messages (历史消息链)                                │
│   - Current Message (任务+规划+历史+截图)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: LLM 请求                                                 │
│ • llm_client.request(messages)                                   │
│ • 返回 LLMResponse (content, thinking, action)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 动作解析                                                 │
│ • ActionParser.parse(response)                                   │
│ • 成功 → 重置错误计数                                            │
│ • 失败 → 计数+1, 达到3次则 ABORT                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: 循环检测                                                 │
│ • loop_detector.check_loop(entries)                              │
│ • 检测: 连续相同动作/滑动/点击相同位置/AB交替                    │
│ • 严重循环 (5+次) → ABORT                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 执行动作                                                 │
│ • action_handler.execute(action)                                 │
│ • 返回 ActionResult (success, should_finish, message)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: 记录历史                                                 │
│ • history_manager.add_action(action, observation, screenshot)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 8: 子任务推进                                               │
│ • _try_advance_subtask(action, current_app)                      │
│ • 基于动作类型和描述匹配判断是否完成当前子任务                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 9: 判断完成                                                 │
│ • action.type in (COMPLETE, ABORT) → finished = True             │
│ • 返回 StepResult                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.2 HistoryManager (`history.py`) - 500行

**职责**: 管理对话历史、构建 LLM 上下文、检测循环

#### 数据结构

```python
@dataclass
class HistoryEntry:
    step: int                         # 步骤编号
    action: Action                    # 执行的动作
    observation: str                  # 屏幕观察 (screen_info)
    screenshot_base64: str | None     # 截图 (可选保存)
    timestamp: datetime               # 时间戳
    user_reply: str | None            # 用户回复 (INFO 动作)
    sub_task_id: int | None           # 所属子任务 ID

@dataclass
class ConversationHistory:
    task: str                         # 原始任务
    entries: list[HistoryEntry]       # 历史记录列表
    qa_history: list[tuple]           # Q&A 历史
    task_plan: TaskPlan | None        # 任务规划
```

#### 上下文构建 (`build_context_messages`)

```
┌────────────────────────────────────────────────────────────────────┐
│                         System Message                              │
│  • 系统提示词 (AutoGLM 或通用格式)                                  │
│  • 动作空间定义                                                     │
│  • 任务完成判断规则                                                 │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                       History Messages                              │
│  [User] Task: xxx                                                   │
│         Observation: 当前应用 com.xxx                               │
│  [Assistant] <think>分析...</think>                                 │
│              {"action_type": "CLICK", "params": {...}}              │
│  [User] Observation: ...                                            │
│  [Assistant] Action: ...                                            │
│  ... (最多 8 步历史)                                                │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Current User Message                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ ## 用户任务                                                   │  │
│  │ 去微信safphere公众号看看第二篇内容，写到备忘录                │  │
│  │                                                               │  │
│  │ ## 任务规划                                                   │  │
│  │ **进度**: 2/9 步骤完成                                        │  │
│  │ ✅ 1. 启动微信                                                │  │
│  │ ✅ 2. 进入搜索或通讯录-公众号                                 │  │
│  │ 🔄 3. 搜索并进入目标公众号 👈 当前                            │  │
│  │ ⬜ 4. 找到并打开指定文章                                      │  │
│  │ ⬜ 5. 阅读并记住文章内容                                      │  │
│  │ ⬜ 6. 返回桌面                                                │  │
│  │ ⬜ 7. 打开备忘录应用                                          │  │
│  │ ⬜ 8. 创建新备忘录                                            │  │
│  │ ⬜ 9. 输入整理好的内容并保存                                  │  │
│  │                                                               │  │
│  │ ### 已执行的操作                                              │  │
│  │ 步骤 1: LAUNCH [微信]                                         │  │
│  │ 步骤 2: CLICK @ [500, 100]                                    │  │
│  │                                                               │  │
│  │ ## 当前屏幕状态                                               │  │
│  │ Current App: com.tencent.mm                                   │  │
│  │                                                               │  │
│  │ **当前目标**: 搜索并进入目标公众号                            │  │
│  │ **请继续执行任务，只有所有步骤完成后才能使用 finish！**       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                         [当前屏幕截图]                              │
└────────────────────────────────────────────────────────────────────┘
```

#### LoopDetector (循环检测器)

| 检测模式 | 阈值 | 示例 |
|----------|------|------|
| 连续相同动作 | 3次 | CLICK→CLICK→CLICK |
| 连续滑动 | 5次 | SWIPE→SWIPE→SWIPE→... |
| 点击相同位置 | 3次 | CLICK@[500,500] 重复 |
| AB交替模式 | 2轮 | CLICK→BACK→CLICK→BACK |

---

### 3.3 TaskPlanner (`planner.py`) - 450行

**职责**: 任务分解、进度跟踪

#### 数据结构

```python
class TaskStatus(Enum):
    PENDING = "pending"           # 待执行
    IN_PROGRESS = "in_progress"   # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    BLOCKED = "blocked"           # 阻塞

@dataclass
class SubTask:
    id: int                       # 子任务 ID
    description: str              # 描述
    status: TaskStatus            # 状态
    app_target: str | None        # 目标应用
    verification: str | None      # 验证条件

@dataclass
class TaskPlan:
    original_task: str            # 原始任务
    sub_tasks: list[SubTask]      # 子任务列表
    current_step: int = 0         # 当前步骤
```

#### 任务分解流程

```
任务输入
    │
    ▼
┌──────────────────────────────┐
│ 1. 模式匹配 (20+ 预定义模式)  │
│   • 微信公众号+备忘录 → 9步   │
│   • 微信发消息 → 4步          │
│   • 淘宝搜索 → 5步            │
│   • 支付宝转账 → 5步          │
│   • ...                       │
└──────────────────────────────┘
    │ 无匹配
    ▼
┌──────────────────────────────┐
│ 2. LLM 动态分解 (Few-shot)    │
│   • 发送 few-shot 示例        │
│   • 解析 JSON 响应            │
└──────────────────────────────┘
    │ 解析失败
    ▼
┌──────────────────────────────┐
│ 3. 兜底计划                   │
│   • 步骤1: 分析任务并开始     │
│   • 步骤2: 完成任务目标       │
└──────────────────────────────┘
```

#### 预定义模式库 (20+ 模式)

| 类别 | 模式 | 步骤数 |
|------|------|--------|
| **微信** | 公众号+备忘录 | 9 |
| | 公众号查看 | 5 |
| | 发消息 | 4 |
| | 朋友圈发布 | 6 |
| | 支付/扫码 | 4 |
| **支付宝** | 转账 | 5 |
| | 付款/扫码 | 3 |
| **购物** | 淘宝搜索 | 5 |
| | 美团外卖 | 5 |
| **社交** | 小红书搜索 | 4 |
| | 抖音搜索 | 4 |
| **工具** | 备忘录 | 4 |
| | 相册 | 3 |
| | 设置 | 3 |
| **通用** | 发送 | 4 |
| | 搜索 | 5 |

---

### 3.4 ActionParser (`actions/parser.py`) - 400行

**职责**: 解析 LLM 输出为结构化动作

#### 支持的格式

**格式 1: Tab 分隔 (gelab-zero 风格)**
```
<THINK>用户要打开微信，我需要先启动应用</THINK>
explain:启动微信应用  action:LAUNCH  value:微信  summary:已启动微信
```

**格式 2: 函数调用 (AutoGLM 风格)**
```
<think>分析当前屏幕，需要点击搜索框</think>
<answer>do(action="Tap", element=[500, 100])</answer>
```

#### 动作类型映射

```python
ACTION_NAME_MAP = {
    # 标准名称
    "CLICK": ActionType.CLICK,
    "SWIPE": ActionType.SWIPE,
    "TYPE": ActionType.TYPE,
    "BACK": ActionType.BACK,
    "HOME": ActionType.HOME,
    "LAUNCH": ActionType.LAUNCH,
    "COMPLETE": ActionType.COMPLETE,
    "ABORT": ActionType.ABORT,
    
    # AutoGLM 别名
    "Tap": ActionType.CLICK,
    "Double Tap": ActionType.DOUBLE_TAP,
    "Long Press": ActionType.LONG_PRESS,
    "Type": ActionType.TYPE,
    "finish": ActionType.COMPLETE,
}
```

---

### 3.5 LLMClient (`llm/client.py`) - 320行

**职责**: 与视觉语言模型通信

#### 配置

```python
@dataclass
class LLMConfig:
    model: str = "gpt-4o"                    # 模型名称
    api_key: str | None = None               # API Key
    api_base: str | None = None              # API Base URL
    max_tokens: int = 4096                   # 最大 token
    temperature: float = 0.7                 # 温度
    timeout: int = 120                       # 超时
    resize_images: bool = True               # 图片压缩
    max_image_size: int = 1024               # 最大图片尺寸
```

#### 响应解析

```python
@dataclass
class LLMResponse:
    content: str           # 完整响应
    thinking: str          # <think>...</think> 内容
    action: str            # <answer>...</answer> 或动作行
    prompt_tokens: int     # 输入 token
    completion_tokens: int # 输出 token
    latency_ms: int        # 延迟
```

---

### 3.6 提示词系统 (`prompts/`)

#### AutoGLM 提示词 (`autoglm.py`)

```
今天的日期是: 2025年12月19日 星期四

你是一个智能手机操作专家...

**重要提醒：你必须始终使用中文思考和回复！**

# 输出格式
<think>{think}</think>
<answer>{action}</answer>

# 任务完成判断 ⚠️ 极其重要
**只有当用户任务的所有步骤都已经完成时，才能使用 finish 结束任务！**

例如任务 "去微信safphere公众号看看第二篇内容，整理好写到备忘录"：
1. ❌ 启动微信后不能结束 - 还没找到公众号
2. ❌ 进入公众号后不能结束 - 还没看第二篇
3. ❌ 看完第二篇后不能结束 - 还没写到备忘录
4. ✅ 写完备忘录后才能结束 - 任务完全完成

# 操作指令
- do(action="Launch", app="xxx")
- do(action="Tap", element=[x,y])
- do(action="Type", text="xxx")
- do(action="Swipe", start=[x1,y1], end=[x2,y2])
- do(action="Back")
- do(action="Home")
- finish(message="xxx")  ← 只有任务完全完成才使用！

# 规则
1. 检查目标app：不是目标app则先 Launch
2. 处理无关页面：先 Back
3. 滑动查找：找不到目标时尝试 Swipe
4. 验证操作：下一步前确认上一步生效
5. 防止过早结束：只有所有子任务都完成才能 finish
```

---

## 四、数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              完整数据流                                  │
└─────────────────────────────────────────────────────────────────────────┘

用户输入: "去微信safphere公众号看看第二篇内容，写到备忘录"
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TaskPlanner.create_plan()                                               │
│ 输入: task                                                              │
│ 输出: TaskPlan (9 个子任务)                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ HistoryManager.start_task()                                             │
│ • 创建 ConversationHistory                                              │
│ • 绑定 TaskPlan                                                         │
│ • 标记第一个子任务为 IN_PROGRESS                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           执行循环开始                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 截屏模块          │    │ 应用检测          │    │ 屏幕信息构建      │
│ take_screenshot() │    │ get_current_app() │    │ build_screen_info│
│ → base64 图片     │    │ → packageName     │    │ → 文本描述       │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ HistoryManager.build_context_messages()                                 │
│ • System Message (提示词)                                               │
│ • History Messages (User/Assistant 交替, 最多 8 步)                     │
│ • Current Message (任务+规划+历史+截图)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LLMClient.request(messages)                                             │
│ → POST /v1/chat/completions                                             │
│ ← LLMResponse { content, thinking, action }                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ActionParser.parse(response)                                            │
│ • 自动检测格式 (Tab / Function Call)                                    │
│ • 提取 thinking 和 action                                               │
│ • 映射动作类型                                                          │
│ → Action { type, params, thinking }                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                │ 解析成功                              │ 解析失败
                ▼                                       ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│ 重置错误计数                  │    │ 错误计数 +1                   │
│ _parse_error_count = 0       │    │ if count >= 3: ABORT         │
└──────────────────────────────┘    │ else: action = WAIT          │
                │                    └──────────────────────────────┘
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LoopDetector.check_loop(entries + new_action)                           │
│ • 连续相同动作检测 (≥3次)                                                │
│ • 点击相同位置检测 (≥3次, 容差50)                                        │
│ • 连续滑动检测 (≥5次)                                                    │
│ • AB 交替模式检测                                                        │
│ → (is_loop, warning_message)                                            │
│ → 严重循环 (5+次) → ABORT                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ActionHandler.execute(action)                                           │
│ • LAUNCH → adb shell monkey -p {package} ...                            │
│ • CLICK → adb shell input tap {x} {y}                                   │
│ • SWIPE → adb shell input swipe {x1} {y1} {x2} {y2}                     │
│ • TYPE → adb shell input text {text}                                    │
│ • BACK → adb shell input keyevent 4                                     │
│ • HOME → adb shell input keyevent 3                                     │
│ → ActionResult { success, should_finish, message }                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ HistoryManager.add_action(action, observation, screenshot)              │
│ • 创建 HistoryEntry                                                     │
│ • 记录 sub_task_id                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PhoneAgent._try_advance_subtask(action, current_app)                    │
│ • LAUNCH 成功且目标应用匹配 → 推进                                       │
│ • CLICK/TYPE 匹配子任务关键词 → 推进                                     │
│ • BACK/HOME 匹配"返回"描述 → 推进                                        │
│ • 同一子任务 3+ 次操作 → 自动推进                                        │
│ → task_plan.mark_current_complete()                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 判断完成                                                                │
│ • action.type == COMPLETE → finished = True, success = True             │
│ • action.type == ABORT → finished = True, success = False               │
│ • step_count >= max_steps → finished = True, stop_reason = max_steps    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │ finished = False              │ finished = True
                    ▼                               ▼
            继续下一步循环                     返回 RunResult
```

---

## 五、文件结构

```
omg_agent/
├── __init__.py
├── core/
│   └── agent/
│       ├── __init__.py              # 模块导出
│       ├── phone_agent.py           # 主控制器 (675行)
│       ├── history.py               # 历史管理 (500行)
│       ├── planner.py               # 任务规划 (450行)
│       ├── session.py               # 会话管理 (270行)
│       ├── actions/
│       │   ├── __init__.py
│       │   ├── space.py            # 动作空间定义
│       │   ├── parser.py           # 动作解析 (400行)
│       │   ├── handler.py          # 动作处理
│       │   └── executor.py         # ADB 执行器
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py           # LLM 客户端 (320行)
│       │   └── message.py          # 消息构建器
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── system.py           # 通用提示词
│       │   └── autoglm.py          # AutoGLM 提示词
│       └── device/
│           ├── __init__.py
│           └── screenshot.py       # 截屏工具
└── gui/
    ├── __init__.py
    ├── main_window.py              # 主窗口
    ├── phone_screen.py             # 手机投屏
    └── ...
```

---

## 六、关键设计决策

| 设计点 | 决策 | 原因 |
|--------|------|------|
| **上下文每步重建** | 每步都包含完整任务描述 | 防止 LLM 忘记目标 |
| **历史限制 8 步** | 仅保留最近 8 步历史 | 平衡上下文长度和效率 |
| **图片仅当前** | 历史消息不含图片 | 节省 token，避免超长 |
| **解析失败不完成** | 解析失败用 WAIT | 防止过早结束 |
| **循环检测先于执行** | 执行前检测循环 | 及时中止无效操作 |
| **子任务自动推进** | 基于动作启发式判断 | 准确跟踪进度 |
| **模式匹配优先** | 预定义模式 > LLM 分解 | 更快且更可靠 |
| **Few-shot LLM 分解** | 提供示例给 LLM | 提高分解质量 |

---

## 七、扩展点

| 模块 | 扩展方式 |
|------|----------|
| **新应用支持** | 在 `TASK_PATTERNS` 添加新模式 |
| **新动作类型** | 在 `ActionType` 和 `ActionParser` 添加 |
| **新模型支持** | 实现新的 prompt 并在 `__post_init__` 选择 |
| **新循环模式** | 在 `LoopDetector.check_loop` 添加检测 |
| **新设备类型** | 在 `device/` 添加新的执行器 |

---

*文档生成时间: 2025-12-19 09:00*
