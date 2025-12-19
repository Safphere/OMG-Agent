# 模型配置指南

<p align="center">
  <a href="model-config.md">English</a> | <a href="model-config_zh.md">中文</a>
</p>

OMG-Agent 支持 OpenAI 兼容 API，本文介绍推荐模型的配置方法。

## 配置界面

点击菜单「设置」→「模型配置」打开配置对话框：

- **API Base URL** - API 服务地址
- **API Key** - 认证密钥
- **模型名称** - 模型标识符

### 高级设置

- **Temperature** - 生成随机性 (0.0-2.0)
- **Max Tokens** - 最大输出长度
- **步骤延迟** - 每步执行间隔
- **自动唤醒屏幕** - 执行前自动亮屏
- **执行前返回主屏** - 执行前按 Home 键

---

## 推荐模型

OMG-Agent 推荐使用以下专门针对手机 GUI 任务训练的模型：

### AutoGLM-Phone-9B（智谱 AI）

智谱 AI 开发的手机 GUI 专用模型，专门针对手机操作任务训练。

**本地部署：**
```
API URL: http://localhost:8000/v1
API Key: EMPTY
Model: autoglm-phone-9b
```

**BigModel API：**
```
API URL: https://open.bigmodel.cn/api/paas/v4
API Key: <your-api-key>
Model: autoglm-phone-9b
```

### GELab-Zero-4B-preview（阶跃星辰）

阶跃星辰开发的手机 Agent 模型，专为移动端 GUI 自动化设计。

```
API URL: https://api.stepfun.com/v1
API Key: <your-api-key>
Model: gelab-zero-4b-preview
```

---

## 本地部署

### vLLM 部署 AutoGLM

```bash
# 安装 vLLM
pip install vllm

# 启动服务
python -m vllm.entrypoints.openai.api_server \
  --model THUDM/autoglm-phone-9b \
  --trust-remote-code \
  --port 8000
```

配置：
```
API URL: http://localhost:8000/v1
API Key: EMPTY
Model: THUDM/autoglm-phone-9b
```

### SGLang 部署

```bash
# 安装
pip install sglang[all]

# 启动
python -m sglang.launch_server \
  --model THUDM/autoglm-phone-9b \
  --port 8000
```

---

## 配置文件

配置保存在 `~/.omg-agent/config.json`：

```json
{
  "api_url": "http://localhost:8000/v1",
  "api_key": "EMPTY",
  "model_name": "autoglm-phone-9b",
  "temperature": 0.7,
  "max_tokens": 4096,
  "step_delay": 1.0,
  "auto_wake": true,
  "reset_home": true
}
```

---

## 模型选择建议

| 场景 | 推荐模型 |
|------|----------|
| 最佳效果 | AutoGLM-Phone-9B (本地部署) |
| 云端使用 | GELab-Zero-4B-preview (阶跃星辰 API) |
| 离线/隐私 | vLLM/SGLang + AutoGLM 本地部署 |
