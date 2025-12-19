# 模拟器配置指南

<p align="center">
  <a href="emulator_setup.md">English</a> | <a href="emulator_setup_zh.md">中文</a>
</p>

OMG-Agent 支持通过 ADB 连接 Android 模拟器进行测试。

相比真机，模拟器在调试和自动化测试方面更加便捷，无需担心电量和设备发热问题。

开启后，我们的Omg-Agent就能连接到MuMu模拟器的ADB了。

OMG-Agent 支持IP连接，方便大家测试模拟器。

模拟器中不需要安装adb-keyboard（目前测试不需要安装）

## 适用场景

*   **开发调试**：快速验证 App 功能。
*   **自动化测试**：稳定的环境运行自动化脚本。
*   **无真机环境**：没有 Android 设备时的替代方案。

## 推荐模拟器列表

| 模拟器名称 | 支持平台 | 特点 | 默认 ADB 端口 | 推荐指数 |
| :--- | :--- | :--- | :--- | :--- |
| **Android Studio Emulator** | Win / Mac | Google 官方，原生纯净，兼容性最佳 | 自动 (5555) | ⭐⭐⭐⭐⭐ |
| **MuMu 模拟器 12** | Win / Mac | 网易出品，性能强劲，系统较新 | 7555 | ⭐⭐⭐⭐ |
| **雷电模拟器 (LDPlayer)** | Win | 轻量级，启动快，资源占用低 | 5555 | ⭐⭐⭐⭐ |
| **夜神模拟器 (Nox)** | Win / Mac | 功能丰富，支持多开 | 62001 | ⭐⭐⭐ |

---

## 详细配置指南

### 1. Android Studio Emulator (官方推荐)

这是 Google 官方提供的模拟器，集成在 Android Studio 开发工具中。

**安装步骤：**
1.  下载并安装 [Android Studio](https://developer.android.com/studio)。
2.  打开 Android Studio，点击 `More Actions` -> `Virtual Device Manager`。
3.  点击 `Create device`，选择一个设备（如 Pixel 6），下载一个系统镜像（推荐 Android 11.0 或以上）。
4.  创建完成后，点击「播放」按钮启动模拟器。

**连接方式：**
*   官方模拟器启动后会自动被 ADB 识别，通常无需手动连接。
*   在终端输入 `adb devices` 即可看到类似 `emulator-5554` 的设备。

### 2. MuMu 模拟器 (MuMu Player)

**安装步骤：**
1.  前往 [MuMu 官网](https://mumu.163.com/) 下载并安装 MuMu 模拟器 12 (Windows) 或 MuMu Pro (Mac)。

![MuMu 官网下载](https://i.meee.com.tw/jIXgwck.png)
2.  **开启 USB 调试**：
    *   Win: 启动模拟器 -> 点击桌面「设置」->「关于平板电脑」-> 连续点击版本号 5-7 次开启开发者模式 -> 返回 ->「系统」->「开发者选项」-> 开启「USB 调试」。

![右上角打开设备设置](https://i.meee.com.tw/8RULV3t.png)

![设置网络，开启桥接模式](https://i.meee.com.tw/tbSDFeK.png)

![在设备设置中打开adb调试](https://i.meee.com.tw/Z5P4XA8.png)

    *   Mac: 通常默认开启，或在菜单栏查找相关设置。

**连接方式：**

```bash
# Windows (MuMu 12 / MuMu 6)
adb connect 127.0.0.1:7555

# 如果连接失败，尝试查看 MuMu 安装目录下的 adb_server.exe 端口占用情况，或使用模拟器自带的 adb 工具。
```

### 3. 雷电模拟器 (LDPlayer)

**安装步骤：**
1.  前往 [雷电模拟器官网](https://www.ldmnq.com/) 下载安装。
2.  启动模拟器，进入「系统应用」->「设置」开启 USB 调试（步骤同上）。
3.  **注意**：雷电模拟器默认开启了 ADB 调试，但建议在模拟器设置中将「root权限」开启（可选，视需求而定）。

**连接方式：**
```bash
adb connect 127.0.0.1:5555
```

### 4. 夜神模拟器 (NoxPlayer)

**安装步骤：**
1.  前往 [夜神官网](https://www.yeshen.com/) 下载安装。
2.  启动模拟器，开启 USB 调试。

**连接方式：**
```bash
adb connect 127.0.0.1:62001
```

---

## 常见问题 (FAQ)

### Q1: 执行 `adb connect` 提示连接失败？

*   **检查端口**：确保端口号正确，不同版本的模拟器端口可能变化。
*   **版本冲突**：电脑上安装的 ADB 版本与模拟器自带的 ADB 版本不一致可能导致冲突。
    *   *解决方法*：将电脑上的 `adb.exe` 复制并替换掉模拟器安装目录下的 `adb.exe` (有时叫 `nox_adb.exe` 等)，保持版本一致。
*   **重启服务**：尝试执行 `adb kill-server` 然后 `adb start-server`。

### Q2: Mac M1/M2/M3 芯片支持吗？
*   Android Studio Emulator 完美支持 ARM 架构 Android 镜像（推荐）。
*   MuMu Pro (Mac) 专为 Apple Silicon 优化。
*   其他模拟器请查看官网最新的兼容性说明。
