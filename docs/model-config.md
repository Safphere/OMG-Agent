# Model Configuration Guide

<p align="center">
  <a href="model-config.md">English</a> | <a href="model-config_zh.md">中文</a>
</p>

OMG-Agent supports OpenAI-compatible APIs. This guide describes how to configure recommended models.

## Configuration Interface

Click menu "Settings" -> "Model Config" to open:

- **API Base URL** - API service address
- **API Key** - Authentication key
- **Model Name** - Model identifier

### Advanced Settings

- **Temperature** - Generation randomness (0.0-2.0)
- **Max Tokens** - Maximum output length
- **Step Delay** - Interval between steps
- **Auto Wake Screen** - Automatically wake screen before execution
- **Reset to Home** - Press Home before execution

---

## Recommended Models

OMG-Agent recommends using models specifically trained for mobile GUI tasks:

### AutoGLM-Phone-9B (Zhipu AI)

Dedicated mobile GUI model by Zhipu AI.

**Local Deployment:**
```
API URL: http://localhost:8000/v1
API Key: EMPTY
Model: autoglm-phone-9b
```

**BigModel API:**
```
API URL: https://open.bigmodel.cn/api/paas/v4
API Key: <your-api-key>
Model: autoglm-phone-9b
```

### GELab-Zero-4B-preview (StepFun)

Mobile Agent model by StepFun.

```
API URL: https://api.stepfun.com/v1
API Key: <your-api-key>
Model: gelab-zero-4b-preview
```

---

## Local Deployment

### Deploy AutoGLM with vLLM

```bash
# Install vLLM
pip install vllm

# Start Server
python -m vllm.entrypoints.openai.api_server \
  --model THUDM/autoglm-phone-9b \
  --trust-remote-code \
  --port 8000
```

Config:
```
API URL: http://localhost:8000/v1
API Key: EMPTY
Model: THUDM/autoglm-phone-9b
```

### Deploy with SGLang

```bash
# Install
pip install sglang[all]

# Start
python -m sglang.launch_server \
  --model THUDM/autoglm-phone-9b \
  --port 8000
```

---

## Configuration File

Configuration is saved in `~/.omg-agent/config.json`:

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

## Model Selection Advice

| Scenario | Recommended Model |
|------|----------|
| Best Performance | AutoGLM-Phone-9B (Local) |
| Cloud Usage | GELab-Zero-4B-preview (StepFun API) |
| Offline/Privacy | vLLM/SGLang + AutoGLM Local |
