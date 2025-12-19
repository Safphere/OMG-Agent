"""
Task Planner - Decompose complex tasks into actionable steps.

This module helps the agent understand and plan multi-step tasks
by breaking them down into clear, sequential sub-tasks.
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class TaskStatus(str, Enum):
    """Status of a task or sub-task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    """A single sub-task within a larger task."""
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    app_target: str | None = None  # Target app for this sub-task
    verification: str | None = None  # How to verify completion
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "app_target": self.app_target,
            "verification": self.verification
        }


@dataclass 
class TaskPlan:
    """A complete plan for executing a task.
    
    The plan is dynamic and can be updated based on execution results.
    Key features:
    - Track progress of each sub-task
    - Insert new steps when needed
    - Skip or modify steps based on actual screen state
    - Support replanning when stuck
    """
    original_task: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    current_step: int = 0
    execution_notes: list[str] = field(default_factory=list)  # 执行过程中的备注
    replanned_count: int = 0  # 重新规划次数
    
    @property
    def current_sub_task(self) -> SubTask | None:
        """Get the current sub-task being worked on."""
        if 0 <= self.current_step < len(self.sub_tasks):
            return self.sub_tasks[self.current_step]
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if all sub-tasks are completed."""
        return all(st.status == TaskStatus.COMPLETED for st in self.sub_tasks)
    
    @property
    def progress_summary(self) -> str:
        """Get a summary of task progress."""
        completed = sum(1 for st in self.sub_tasks if st.status == TaskStatus.COMPLETED)
        total = len(self.sub_tasks)
        return f"{completed}/{total} 步骤完成"
    
    @property
    def remaining_steps(self) -> list[SubTask]:
        """Get remaining uncompleted sub-tasks."""
        return [st for st in self.sub_tasks if st.status != TaskStatus.COMPLETED]
    
    def mark_current_complete(self) -> None:
        """Mark current sub-task as complete and move to next."""
        if self.current_sub_task:
            self.current_sub_task.status = TaskStatus.COMPLETED
            self.current_step += 1
    
    def mark_current_failed(self, reason: str = "") -> None:
        """Mark current sub-task as failed."""
        if self.current_sub_task:
            self.current_sub_task.status = TaskStatus.FAILED
            self.execution_notes.append(f"步骤{self.current_step + 1}失败: {reason}")
    
    def skip_current(self, reason: str = "") -> None:
        """Skip current sub-task (e.g., already done by previous action)."""
        if self.current_sub_task:
            self.current_sub_task.status = TaskStatus.COMPLETED
            self.execution_notes.append(f"跳过步骤{self.current_step + 1}: {reason}")
            self.current_step += 1
    
    def insert_step(self, description: str, verification: str = None, position: int = None) -> None:
        """Insert a new step into the plan.
        
        Args:
            description: What needs to be done
            verification: How to verify completion
            position: Where to insert (None = after current step)
        """
        if position is None:
            position = self.current_step + 1
        
        new_step = SubTask(
            id=0,  # Will be renumbered
            description=description,
            verification=verification,
            status=TaskStatus.PENDING
        )
        self.sub_tasks.insert(position, new_step)
        self._renumber_steps()
        self.execution_notes.append(f"新增步骤: {description}")
    
    def _renumber_steps(self) -> None:
        """Renumber all steps after modification."""
        for i, st in enumerate(self.sub_tasks):
            st.id = i + 1
    
    def update_from_observation(self, screen_state: str, last_action: str) -> str | None:
        """
        Update plan based on current screen observation.
        
        Returns:
            Suggestion for next action, or None if plan is on track
        """
        if not screen_state:
            return None
            
        suggestions = []
        
        # 检测是否需要登录
        login_keywords = ["登录", "登入", "sign in", "login", "账号", "密码"]
        if any(kw in screen_state.lower() for kw in login_keywords):
            suggestions.append("检测到登录页面，可能需要 TAKE_OVER 让用户登录")
        
        # 检测是否在加载中
        loading_keywords = ["加载中", "loading", "请稍候", "正在加载"]
        if any(kw in screen_state.lower() for kw in loading_keywords):
            suggestions.append("页面正在加载，建议 WAIT 等待")
        
        # 检测是否出现弹窗
        popup_keywords = ["确定", "取消", "允许", "拒绝", "知道了", "close", "dismiss"]
        if any(kw in screen_state.lower() for kw in popup_keywords):
            suggestions.append("检测到弹窗，可能需要先处理")
        
        return "; ".join(suggestions) if suggestions else None
    
    def suggest_recovery(self, stuck_count: int) -> str:
        """Suggest recovery action when stuck.
        
        Args:
            stuck_count: How many times the same action was repeated
            
        Returns:
            Suggested recovery action
        """
        if stuck_count >= 5:
            return "多次重复操作，建议 ABORT 或 TAKE_OVER"
        elif stuck_count >= 3:
            return "操作似乎卡住，尝试 BACK 返回或 HOME 回到桌面重新开始"
        elif stuck_count >= 2:
            return "操作似乎无效，尝试不同位置或方法"
        return ""
    
    def to_prompt(self, lang: str = "zh") -> str:
        """Generate prompt text describing the task plan."""
        if lang == "zh":
            lines = ["## 任务规划\n"]
            lines.append(f"**原始任务**: {self.original_task}\n")
            lines.append(f"**进度**: {self.progress_summary}\n")
            lines.append("\n**步骤列表**:")
            
            for st in self.sub_tasks:
                if st.status == TaskStatus.COMPLETED:
                    status_icon = "✅"
                elif st.status == TaskStatus.IN_PROGRESS:
                    status_icon = "🔄"
                elif st.status == TaskStatus.FAILED:
                    status_icon = "❌"
                else:
                    status_icon = "⬜"
                
                current_marker = " 👈 **当前**" if st.id == self.current_step + 1 else ""
                lines.append(f"{status_icon} {st.id}. {st.description}{current_marker}")
            
            if self.current_sub_task:
                lines.append(f"\n**当前目标**: {self.current_sub_task.description}")
                if self.current_sub_task.verification:
                    lines.append(f"**完成标志**: {self.current_sub_task.verification}")
        else:
            lines = ["## Task Plan\n"]
            lines.append(f"**Original Task**: {self.original_task}\n")
            lines.append(f"**Progress**: {self.progress_summary}\n")
            lines.append("\n**Steps**:")
            
            for st in self.sub_tasks:
                if st.status == TaskStatus.COMPLETED:
                    status_icon = "✅"
                elif st.status == TaskStatus.IN_PROGRESS:
                    status_icon = "🔄"
                elif st.status == TaskStatus.FAILED:
                    status_icon = "❌"
                else:
                    status_icon = "⬜"
                
                current_marker = " 👈 **Current**" if st.id == self.current_step + 1 else ""
                lines.append(f"{status_icon} {st.id}. {st.description}{current_marker}")
            
            if self.current_sub_task:
                lines.append(f"\n**Current Goal**: {self.current_sub_task.description}")
                if self.current_sub_task.verification:
                    lines.append(f"**Completion Check**: {self.current_sub_task.verification}")
        
        # 添加剩余步骤提醒
        remaining = len(self.remaining_steps)
        if remaining > 0:
            if lang == "zh":
                lines.append(f"\n⚠️ **还有 {remaining} 个步骤未完成，不要提前结束任务！**")
            else:
                lines.append(f"\n⚠️ **{remaining} steps remaining, do NOT complete task prematurely!**")
        
        # 添加执行备注（如果有）
        if self.execution_notes:
            if lang == "zh":
                lines.append("\n**执行备注**:")
            else:
                lines.append("\n**Execution Notes**:")
            for note in self.execution_notes[-3:]:  # 只显示最近3条
                lines.append(f"- {note}")
        
        return "\n".join(lines)


class TaskPlanner:
    """
    Plans and decomposes complex tasks into actionable steps.
    
    Uses pattern matching for common task types and can optionally
    use LLM for dynamic task decomposition.
    """
    
    # Common task patterns and their decomposition
    # ORDER MATTERS: More specific patterns should come first!
    TASK_PATTERNS = [
        # ==================== 跨应用复合任务（最高优先级）====================
        # 查价格+整理到备忘录类
        (r"(淘宝|京东|拼多多).*价格.*备忘录|价格.*整理.*备忘录", [
            ("启动购物App", None, "看到购物App主界面"),
            ("点击搜索框", None, "搜索框激活"),
            ("输入商品关键词", None, "搜索结果出现"),
            ("仔细查看商品列表和价格信息", None, "已记住价格信息"),
            ("记下多个商品的名称和价格", None, "已记录3-5款商品价格"),
            ("返回桌面", None, "看到桌面"),
            ("打开备忘录应用", None, "看到备忘录界面"),
            ("创建新备忘录", None, "看到编辑界面"),
            ("输入整理好的价格信息并保存", None, "备忘录已保存"),
        ]),
        # 搜索+备忘录通用模式
        (r".*查.*然后.*整理.*备忘录|.*搜.*然后.*记.*备忘录", [
            ("打开相关App查询信息", None, "看到App主界面"),
            ("执行搜索操作", None, "搜索结果出现"),
            ("仔细阅读和记住关键信息", None, "已记录关键信息"),
            ("返回桌面", None, "看到桌面"),
            ("打开备忘录应用", None, "看到备忘录界面"),
            ("创建新备忘录并输入内容", None, "内容已输入"),
            ("保存备忘录", None, "备忘录已保存"),
        ]),
        # 复制+粘贴跨应用
        (r".*复制.*粘贴.*|.*从.*复制.*到", [
            ("打开源应用", None, "看到源应用界面"),
            ("找到要复制的内容", None, "看到目标内容"),
            ("长按选择并复制", None, "内容已复制"),
            ("返回桌面", None, "看到桌面"),
            ("打开目标应用", None, "看到目标应用界面"),
            ("找到输入位置", None, "输入框可用"),
            ("粘贴内容", None, "内容已粘贴"),
            ("保存或发送", None, "操作完成"),
        ]),
        # ==================== 微信相关 ====================
        # 最具体的模式优先
        (r"微信.*公众号.*备忘录|备忘录.*微信.*公众号", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("进入搜索或通讯录-公众号", None, "看到公众号入口"),
            ("搜索并进入目标公众号", None, "看到公众号主页"),
            ("找到并打开指定文章", None, "看到文章详情"),
            ("阅读并记住文章内容", None, "已了解文章要点"),
            ("返回桌面", None, "看到桌面"),
            ("打开备忘录应用", None, "看到备忘录界面"),
            ("创建新备忘录", None, "看到编辑界面"),
            ("输入整理好的内容并保存", None, "备忘录已保存"),
        ]),
        (r"微信.*公众号.*内容|微信.*公众号.*文章|微信.*公众号.*看", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("进入搜索或通讯录-公众号", None, "看到公众号入口"),
            ("搜索并进入目标公众号", None, "看到公众号主页"),
            ("找到并打开指定文章", None, "看到文章详情"),
            ("阅读文章内容", None, "已查看完整内容"),
        ]),
        (r"微信.*公众号", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("点击搜索或通讯录", None, "看到搜索界面或公众号入口"),
            ("搜索并进入公众号", None, "看到公众号主页"),
            ("查看指定内容", None, "看到文章内容"),
        ]),
        (r"微信.*发.*消息|发.*消息.*微信|微信.*说", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("搜索或找到联系人", None, "看到联系人聊天界面"),
            ("输入消息内容", None, "消息出现在输入框"),
            ("点击发送按钮", None, "消息出现在聊天记录中"),
        ]),
        (r"微信.*朋友圈.*发|发.*朋友圈", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("点击发现", None, "看到发现页面"),
            ("点击朋友圈", None, "看到朋友圈"),
            ("点击右上角相机/发布按钮", None, "看到发布界面"),
            ("输入内容或选择图片", None, "内容已准备"),
            ("点击发表", None, "发布成功"),
        ]),
        (r"微信.*朋友圈", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("点击发现", None, "看到发现页面"),
            ("点击朋友圈", None, "看到朋友圈"),
            ("浏览朋友圈内容", None, "操作完成"),
        ]),
        (r"微信.*支付|微信.*转账|微信.*红包", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("进入我-服务/支付", None, "看到支付界面"),
            ("执行支付操作", None, "支付流程进行中"),
            ("确认支付", None, "支付完成"),
        ]),
        (r"微信.*扫一扫|微信.*扫码", [
            ("启动微信", "com.tencent.mm", "看到微信主界面"),
            ("点击右上角+号", None, "看到菜单"),
            ("点击扫一扫", None, "相机打开"),
            ("扫描二维码", None, "扫描完成"),
        ]),
        # ==================== 支付宝相关 ====================
        (r"支付宝.*转账|转账.*支付宝", [
            ("启动支付宝", "com.eg.android.AlipayGphone", "看到支付宝主界面"),
            ("点击转账", None, "看到转账界面"),
            ("输入转账对象", None, "已选择收款人"),
            ("输入金额", None, "金额已输入"),
            ("确认转账", None, "转账成功"),
        ]),
        (r"支付宝.*付款|支付宝.*支付", [
            ("启动支付宝", "com.eg.android.AlipayGphone", "看到支付宝主界面"),
            ("进入付款/收款", None, "看到付款界面"),
            ("完成支付操作", None, "支付完成"),
        ]),
        (r"支付宝.*扫一扫|支付宝.*扫码", [
            ("启动支付宝", "com.eg.android.AlipayGphone", "看到支付宝主界面"),
            ("点击扫一扫", None, "相机打开"),
            ("扫描二维码", None, "扫描完成"),
        ]),
        # ==================== 淘宝/购物相关 ====================
        (r"淘宝.*搜索|淘宝.*找|淘宝.*买", [
            ("启动淘宝", "com.taobao.taobao", "看到淘宝主界面"),
            ("点击搜索框", None, "搜索框激活"),
            ("输入搜索关键词", None, "搜索结果出现"),
            ("选择合适的商品", None, "进入商品详情"),
            ("执行后续操作", None, "操作完成"),
        ]),
        (r"美团.*点餐|美团.*外卖", [
            ("启动美团", "com.sankuai.meituan", "看到美团主界面"),
            ("进入外卖", None, "看到外卖界面"),
            ("搜索或选择餐厅", None, "看到餐厅/菜单"),
            ("选择菜品", None, "菜品已加入购物车"),
            ("下单", None, "订单已提交"),
        ]),
        # ==================== 社交媒体 ====================
        (r"小红书.*搜索|小红书.*找|小红书.*看", [
            ("启动小红书", "com.xingin.xhs", "看到小红书主界面"),
            ("点击搜索", None, "搜索框激活"),
            ("输入搜索关键词", None, "搜索结果出现"),
            ("查看内容", None, "内容已加载"),
        ]),
        (r"抖音.*搜索|抖音.*找|抖音.*看", [
            ("启动抖音", "com.ss.android.ugc.aweme", "看到抖音主界面"),
            ("点击搜索", None, "搜索框激活"),
            ("输入搜索关键词", None, "搜索结果出现"),
            ("查看视频", None, "视频播放中"),
        ]),
        # ==================== 工具类 ====================
        (r"备忘录.*写|备忘录.*记|写.*备忘录|记.*备忘录", [
            ("打开备忘录", None, "看到备忘录界面"),
            ("创建新备忘录", None, "看到编辑界面"),
            ("输入内容", None, "内容已输入"),
            ("保存", None, "备忘录已保存"),
        ]),
        (r"相册.*看|相册.*找|查看.*照片", [
            ("打开相册", None, "看到相册界面"),
            ("找到目标照片", None, "看到照片"),
            ("查看或操作", None, "操作完成"),
        ]),
        (r"打开.*设置|设置.*修改", [
            ("启动设置应用", None, "看到设置主界面"),
            ("找到目标设置项", None, "看到目标选项"),
            ("修改设置", None, "设置已更改"),
        ]),
        # ==================== 通用模式 ====================
        (r"打开.*发送|发送.*给", [
            ("启动目标应用", None, "应用已打开"),
            ("导航到发送界面", None, "看到发送入口"),
            ("输入内容", None, "内容已输入"),
            ("发送", None, "发送成功"),
        ]),
        (r"搜索|查找|找", [
            ("确定搜索场景", None, "明确搜索目标"),
            ("打开相关应用", None, "应用已打开"),
            ("点击搜索框", None, "搜索框激活"),
            ("输入搜索内容", None, "搜索结果出现"),
            ("查看结果", None, "找到目标"),
        ]),
    ]
    
    @classmethod
    def create_plan(cls, task: str, use_llm: bool = False, llm_client: Any = None) -> TaskPlan:
        """
        Create a task plan by decomposing the task into sub-tasks.
        
        Args:
            task: The original task description
            use_llm: Whether to use LLM for dynamic decomposition
            llm_client: LLM client for dynamic decomposition
            
        Returns:
            TaskPlan with sub-tasks
        """
        import re
        
        # Try pattern matching first (patterns are ordered by specificity)
        for pattern, steps in cls.TASK_PATTERNS:
            if re.search(pattern, task):
                sub_tasks = []
                for i, (desc, app, verify) in enumerate(steps, 1):
                    sub_tasks.append(SubTask(
                        id=i,
                        description=desc,
                        app_target=app,
                        verification=verify
                    ))
                return TaskPlan(original_task=task, sub_tasks=sub_tasks)
        
        # Use LLM for dynamic decomposition if available
        if use_llm and llm_client:
            return cls._decompose_with_llm(task, llm_client)
        
        # Fallback: create a generic single-step plan
        return TaskPlan(
            original_task=task,
            sub_tasks=[
                SubTask(id=1, description="分析任务并开始执行", verification="任务已开始"),
                SubTask(id=2, description="完成任务目标", verification="目标已达成"),
            ]
        )
    
    @classmethod
    def _decompose_with_llm(cls, task: str, llm_client: Any) -> TaskPlan:
        """Use LLM to dynamically decompose a task."""
        prompt = f"""你是一个手机操作专家。请将以下任务分解为清晰、完整的执行步骤。

⚠️ 重要规则：
1. 分解出的步骤必须覆盖任务的【所有部分】
2. 如果任务涉及多个App，需要包含"返回桌面"和"打开下一个App"的步骤
3. 如果需要"整理"或"保存"到其他地方，必须包含完整的保存流程

任务: {task}

示例1 - 单App任务:
任务: "用微信给张三发消息说明天见"
输出:
```json
[
  {{"id": 1, "description": "启动微信", "app_target": "com.tencent.mm", "verification": "看到微信主界面"}},
  {{"id": 2, "description": "点击搜索框", "app_target": null, "verification": "搜索框激活"}},
  {{"id": 3, "description": "搜索联系人张三", "app_target": null, "verification": "看到搜索结果"}},
  {{"id": 4, "description": "点击进入聊天", "app_target": null, "verification": "看到聊天界面"}},
  {{"id": 5, "description": "输入消息明天见", "app_target": null, "verification": "消息出现在输入框"}},
  {{"id": 6, "description": "点击发送", "app_target": null, "verification": "消息发送成功"}}
]
```

示例2 - 跨App任务（查询+保存）:
任务: "去淘宝查Mac Mini M4的价格，然后整理到备忘录"
输出:
```json
[
  {{"id": 1, "description": "启动淘宝", "app_target": "com.taobao.taobao", "verification": "看到淘宝主界面"}},
  {{"id": 2, "description": "点击搜索框", "app_target": null, "verification": "搜索框激活"}},
  {{"id": 3, "description": "输入Mac Mini M4", "app_target": null, "verification": "搜索结果出现"}},
  {{"id": 4, "description": "仔细查看并记住几款商品的价格", "app_target": null, "verification": "已记录价格信息"}},
  {{"id": 5, "description": "按HOME返回桌面", "app_target": null, "verification": "看到桌面"}},
  {{"id": 6, "description": "打开备忘录应用", "app_target": null, "verification": "看到备忘录界面"}},
  {{"id": 7, "description": "创建新备忘录", "app_target": null, "verification": "看到编辑界面"}},
  {{"id": 8, "description": "输入整理好的价格信息", "app_target": null, "verification": "内容已输入"}},
  {{"id": 9, "description": "保存备忘录", "app_target": null, "verification": "备忘录已保存"}}
]
```

请输出任务的完整步骤列表（只输出 JSON，不要解释）：
```json
"""
        
        try:
            import json
            response = llm_client.request([{
                "role": "user",
                "content": prompt
            }], max_tokens=1024, temperature=0.3)
            
            # Extract JSON from response
            content = response.content
            json_match = content.find("[")
            if json_match != -1:
                json_end = content.rfind("]") + 1
                json_str = content[json_match:json_end]
                steps = json.loads(json_str)
                
                sub_tasks = []
                for step in steps:
                    sub_tasks.append(SubTask(
                        id=step.get("id", len(sub_tasks) + 1),
                        description=step.get("description", ""),
                        app_target=step.get("app_target"),
                        verification=step.get("verification")
                    ))
                
                return TaskPlan(original_task=task, sub_tasks=sub_tasks)
        except Exception as e:
            pass  # Fall through to default
        
        # Fallback
        return TaskPlan(
            original_task=task,
            sub_tasks=[
                SubTask(id=1, description="执行任务", verification="任务完成"),
            ]
        )


def analyze_task_complexity(task: str) -> dict[str, Any]:
    """
    Analyze the complexity of a task.
    
    Returns:
        Dict with complexity info: estimated_steps, apps_involved, action_types
    """
    import re
    
    # Keywords that indicate multiple steps
    multi_step_keywords = [
        "然后", "之后", "接着", "并且", "同时",
        "第一", "第二", "第三",
        "首先", "最后", "完成后",
        "and then", "after", "next", "finally"
    ]
    
    # Keywords for different action types
    action_keywords = {
        "input": ["输入", "写", "发送", "type", "send", "write"],
        "navigation": ["打开", "进入", "找到", "搜索", "open", "find", "search"],
        "interaction": ["点击", "滑动", "长按", "click", "tap", "swipe"],
        "read": ["看", "查看", "阅读", "读", "view", "read", "check"],
    }
    
    # App name patterns
    app_patterns = [
        "微信", "WeChat", "QQ", "淘宝", "支付宝", "Alipay",
        "抖音", "TikTok", "小红书", "美团", "饿了么",
        "备忘录", "Notes", "设置", "Settings", "相册", "Photos"
    ]
    
    # Count multi-step indicators
    step_indicators = sum(1 for kw in multi_step_keywords if kw in task)
    
    # Identify action types
    actions_found = []
    for action_type, keywords in action_keywords.items():
        if any(kw in task for kw in keywords):
            actions_found.append(action_type)
    
    # Identify apps
    apps_found = [app for app in app_patterns if app in task]
    
    # Estimate complexity
    estimated_steps = max(2, step_indicators + len(apps_found) + len(actions_found))
    
    return {
        "estimated_steps": min(estimated_steps, 10),  # Cap at 10
        "apps_involved": apps_found,
        "action_types": actions_found,
        "is_complex": estimated_steps > 3 or len(apps_found) > 1,
    }
