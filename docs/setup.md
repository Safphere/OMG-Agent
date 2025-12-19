# Environment Setup Guide

<p align="center">
  <a href="setup.md">English</a> | <a href="setup_zh.md">中文</a>
</p>

## Windows Configuration

### 1. Install ADB

**Option 1: Using Scoop (Recommended)**
```bash
# Install Scoop (if not installed)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# Install ADB
scoop install adb
```

**Option 2: Using Winget**
```bash
winget install Google.PlatformTools
```

**Option 3: Manual Installation**
1. Download [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools).
2. Extract to any directory (e.g., `C:\adb`).
3. Add the directory to the system PATH environment variable.

Verify installation:
```bash
adb version
```

### 2. Install Python 3.10+

Recommended to use [Python Official Installer](https://www.python.org/downloads/) or Scoop:

```bash
scoop install python
```

---

## macOS Configuration

### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install ADB

```bash
brew install android-platform-tools
```

### 3. Install Python 3.10+

```bash
brew install python@3.11
```

---

## Phone Configuration

### 1. Enable Developer Options

1. Open "Settings" -> "About Phone".
2. Tap "Build Number" 7 times continuously.
3. Return to Settings, find "Developer Options".

### 2. Enable USB Debugging

In "Developer Options":
- Enable "USB Debugging".
- Enable "USB Debugging (Security Settings)" (Required for some Xiaomi/Redmi phones).

### 3. Install ADBKeyboard

To allow the Agent to input Chinese and special characters, a dedicated input method is required:

1. Download: [ADBKeyboard.apk](https://github.com/nicekwell/ADBKeyboard/releases).
2. Install APK to phone.
3. Settings -> Language & Input -> Enable "ADB Keyboard".
4. Switch to ADB Keyboard when using (can be switched in notification bar).

### 4. Connection Test

```bash
# After USB connection
adb devices

# Should see output like:
# List of devices attached
# XXXXXXXX    device
```

---

## Wireless Connection (Optional)

### Method 1: WiFi ADB

1. Connect phone via USB first.
2. Ensure phone and computer are on the same WiFi.
3. Execute:
   ```bash
   adb tcpip 5555
   adb connect <PhoneIP>:5555
   ```
4. Unplug USB cable.

### Method 2: Wireless Debugging (Android 11+)

1. Developer Options -> Wireless Debugging -> Enable.
2. Tap "Pair device with pairing code".
3. On computer execute:
   ```bash
   adb pair <IP>:<PairPort> <PairCode>
   adb connect <IP>:<ConnectPort>
   ```

---

## FAQ

### ADB Device Not Found

1. Check if USB cable supports data transfer.
2. Change USB port.
3. Check if phone has authorized debugging.
4. Restart ADB: `adb kill-server && adb start-server`.

### Cannot Input Chinese

Ensure [ADBKeyboard](https://github.com/nicekwell/ADBKeyboard) is installed and enabled.
