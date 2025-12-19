# 环境配置详解

<p align="center">
  <a href="setup.md">English</a> | <a href="setup_zh.md">中文</a>
</p>

## Windows 配置

### 1. 安装 ADB

**方式一：使用 Scoop（推荐）**
```bash
# 安装 Scoop（如未安装）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# 安装 ADB
scoop install adb
```

**方式二：使用 Winget**
```bash
winget install Google.PlatformTools
```

**方式三：手动安装**
1. 下载 [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. 解压到任意目录（如 `C:\adb`）
3. 将目录添加到系统 PATH 环境变量

验证安装：
```bash
adb version
```


### 2. 安装 Python 3.10+

推荐使用 [Python 官方安装包](https://www.python.org/downloads/) 或 Scoop：

```bash
scoop install python
```

---

## macOS 配置

### 1. 安装 Homebrew（如未安装）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. 安装 ADB

```bash
brew install android-platform-tools
```

### 3. 安装 Python 3.10+

```bash
brew install python@3.11
```

---

## 手机端配置

### 1. 开启开发者选项

1. 打开「设置」→「关于手机」
2. 连续点击「版本号」7 次
3. 返回设置，找到「开发者选项」

### 2. 开启 USB 调试

在「开发者选项」中：
- 开启「USB 调试」
- 开启「USB 调试（安全设置）」（部分手机需要）

### 3. 安装 ADBKeyboard 输入法

为了让 Agent 能够输入中文和特殊字符，需要安装专用输入法：

1. 下载：[ADBKeyboard.apk](https://github.com/nicekwell/ADBKeyboard/releases)
2. 安装 APK 到手机
3. 设置 → 语言和输入法 → 启用「ADB Keyboard」
4. 使用时切换为 ADB Keyboard（可在通知栏切换）

### 4. 连接测试

```bash
# USB 连接后
adb devices

# 应该看到类似输出：
# List of devices attached
# XXXXXXXX    device
```

---

## 无线连接（可选）

### 方式一：WiFi ADB

1. 先通过 USB 连接手机
2. 确保手机和电脑在同一 WiFi
3. 执行：
   ```bash
   adb tcpip 5555
   adb connect <手机IP>:5555
   ```
4. 拔掉 USB 线

### 方式二：无线调试（Android 11+）

1. 开发者选项 → 无线调试 → 开启
2. 点击「使用配对码配对设备」
3. 在电脑执行：
   ```bash
   adb pair <IP>:<配对端口> <配对码>
   adb connect <IP>:<连接端口>
   ```

---

## 常见问题

### ADB 找不到设备

1. 检查 USB 线是否支持数据传输
2. 更换 USB 端口
3. 检查手机是否授权调试
4. 重启 ADB：`adb kill-server && adb start-server`


### 无法输入中文

确保已安装并启用 ADBKeyboard 输入法。
