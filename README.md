<div align="center">
  <img src="assets/logo.png" width="128" alt="OMG-Agent Logo">
  <h1>OMG-Agent</h1>

  <p>
    <strong>Open-sourced Mobile GUI Agent</strong>
    <br>
    Open-source, universal Mobile GUI Agent framework
  </p>

  <p>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
    </a>
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg" alt="Platform">
  </p>

  <p align="center">
    <a href="README.md">English</a> | <a href="README_zh.md">中文</a>
  </p>

  <br>
  <img src="https://i.meee.com.tw/TWKyoTe.gif" width="100%" alt="OMG-Agent Preview">
  <br>
  <br>
</div>

---

## Introduction

OMG-Agent is an open-source Mobile GUI Agent desktop client that drives AI to automatically operate Android phones via natural language instructions.

**Core Features:**
- Supports Mobile GUI models like AutoGLM and GELab-Zero
- ADB Real-time Screenshot + AI Task Execution
- Bilingual Interface (English/Chinese), Dark/Light Themes
- Supports OpenAI-compatible API
- Supports Android Emulators

> **⚠️ Disclaimer**
>
> This project is for learning, research, and technical exploration only. **Strictly prohibited for any commercial use.** When using this tool, please comply with relevant laws and regulations, as well as the terms of use and service agreements of mobile phone manufacturers and applications. Users are solely responsible for any actions and consequences arising from the use of this project, which are unrelated to this project and its developers.

## Quick Start

### 1. Prerequisites

```bash
# Install ADB
scoop install adb  # Windows
brew install android-platform-tools  # macOS
apt install adb  # Linux (Ubuntu)
```

### 2. Installation

```bash
git clone https://github.com/safphere/OMG-Agent.git
cd OMG-Agent
pip install -r requirements.txt
python run.py
```

### 3. Phone Setup

1. Enable "Developer Options" and "USB Debugging".
2. Install [ADBKeyboard](https://github.com/nicekwell/ADBKeyboard/releases).
3. Connect phone via USB and allow debugging authorization.

### 4. Usage

1. Click "Refresh Devices".
2. Click "Start Screen".
3. Enter task (e.g., "Open WeChat and send a message to John").
4. Click "Execute".

## Supported Models

| Model | Source | Description |
|------|------|------|
| **AutoGLM-Phone-9B** | Zhipu AI | Dedicated Mobile GUI Model |
| **GELab-Zero-4B-preview** | StepFun | Mobile Agent Model |

These models are specifically trained for Mobile GUI tasks and are recommended.

## Documentation
For users without Android phones, refer to the [Emulator Setup Guide](docs/emulator_setup.md).

- [Environment Setup](docs/setup.md)
- [Model Configuration](docs/model-config.md)
- [Development Guide](docs/development.md)

## Project Structure

```
OMG-Agent/
├── omg_agent/
│   ├── gui/           # GUI Interface
│   └── core/
│       ├── agent/     # AI Agent Core
│       └── config.py  # Config Management
├── assets/            # Assets
├── docs/              # Documentation
└── run.py             # Entry Point
```

---

## About Safphere

**Safphere** is an open-source community composed of algorithm engineers and university geeks, focusing on technical exploration and knowledge sharing in the AI field.

<p align="center">
  <img src="https://raw.githubusercontent.com/Safphere/.github/main/profile/src/wechat.svg" alt="Safphere WeChat" height="150" />
</p>

<p align="center">
  <img src="https://i.meee.com.tw/HhFX1lb.jpg" alt="Project Group" width="200" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="https://i.meee.com.tw/ZGXK6FC.jpg" alt="Contact Author" width="200" />
</p>


| Platform | Link |
|------|------|
| GitHub | [github.com/safphere](https://github.com/safphere) |
| WeChat Official | Safphere |
| Social Media | @Safphere |

⭐ If you find this project helpful, please **Star** us!

## License

This project is licensed under the **Apache License 2.0 with Commons Clause**.

- ✅ Learning, research, and personal use allowed
- ✅ Modification and secondary development allowed
- ❌ Commercial use prohibited
- ⚠️ Please credit the source when using

See [LICENSE](./LICENSE) for details.

## Acknowledgements

- [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) — Zhipu AI Mobile GUI Model
- [gelab-zero](https://github.com/stepfun-ai/gelab-zero) — StepFun Mobile Agent Framework
- [ADBKeyboard](https://github.com/nicekwell/ADBKeyboard) — ADB Input Method

---

© 2025 [Safphere](https://github.com/safphere)
