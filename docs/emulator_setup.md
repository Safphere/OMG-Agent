# Emulator Setup Guide

<p align="center">
  <a href="emulator_setup.md">English</a> | <a href="emulator_setup_zh.md">中文</a>
</p>

OMG-Agent supports testing via ADB connection to Android emulators.

Compared to real devices, emulators are more convenient for debugging and automated testing, without worrying about battery or heating issues.

## Applicable Scenarios

*   **Development & Debugging**: Quickly verify App functions.
*   **Automated Testing**: Stable environment for running automation scripts.
*   **No Real Device**: Alternative solution when no Android device is available.

## Recommended Emulators

| Emulator Name | Platform | Features | Default ADB Port | Rating |
| :--- | :--- | :--- | :--- | :--- |
| **Android Studio Emulator** | Win / Mac | Official Google, pure native, best compatibility | Automatic (5555) | ⭐⭐⭐⭐⭐ |
| **MuMu Player 12** | Win / Mac | Netease, strong performance, newer system | 7555 | ⭐⭐⭐⭐ |
| **LDPlayer** | Win | Lightweight, fast startup, low resource usage | 5555 | ⭐⭐⭐⭐ |
| **NoxPlayer** | Win / Mac | Feature-rich, supports multi-instance | 62001 | ⭐⭐⭐ |

---

## Detailed Configuration Guide

### 1. Android Studio Emulator (Official Recommended)

This is the official emulator provided by Google, integrated into Android Studio.

**Installation:**
1.  Download and install [Android Studio](https://developer.android.com/studio).
2.  Open Android Studio, click `More Actions` -> `Virtual Device Manager`.
3.  Click `Create device`, select a device (e.g., Pixel 6), download a system image (Android 11.0+ recommended).
4.  After creation, click the "Play" button to start the emulator.

**Connection:**
*   Official emulators are automatically recognized by ADB after startup, usually no manual connection needed.
*   Type `adb devices` in terminal to see devices like `emulator-5554`.

### 2. MuMu Player

**Installation:**
1.  Go to [MuMu Official Site](https://mumu.163.com/) to download and install MuMu Player 12 (Windows) or MuMu Pro (Mac).

![MuMu Download](https://i.meee.com.tw/jIXgwck.png)

2.  **Enable USB Debugging**:
    *   Win: Start Emulator -> Click "Settings" on desktop -> "About Tablet" -> Tap "Build Number" 5-7 times -> Return -> "System" -> "Developer Options" -> Enable "USB Debugging".

![Settings](https://i.meee.com.tw/8RULV3t.png)
![Bridge Mode](https://i.meee.com.tw/tbSDFeK.png)
![ADB Debugging](https://i.meee.com.tw/Z5P4XA8.png)

    *   Mac: Usually enabled by default.

**Connection:**

```bash
# Windows (MuMu 12 / MuMu 6)
adb connect 127.0.0.1:7555
```

### 3. LDPlayer

**Installation:**
1.  Download from [LDPlayer Official Site](https://www.ldmnq.com/).
2.  Start emulator, go to "System Apps" -> "Settings" to enable USB Debugging.
3.  **Note**: LDPlayer enables ADB by default, but it's recommended to enable "Root Permission" in emulator settings if needed.

**Connection:**
```bash
adb connect 127.0.0.1:5555
```

### 4. NoxPlayer

**Installation:**
1.  Download from [Nox Official Site](https://www.bignox.com/).
2.  Start emulator, enable USB Debugging.

**Connection:**
```bash
adb connect 127.0.0.1:62001
```

---

## FAQ

### Q1: `adb connect` fails?

*   **Check Port**: Ensure port number is correct.
*   **Version Conflict**: ADB version on computer and emulator must match.
    *   *Solution*: Copy `adb.exe` from computer to replace the one in emulator installation directory.
*   **Restart Service**: Try `adb kill-server` and `adb start-server`.

### Q2: Is Mac M1/M2/M3 supported?
*   Android Studio Emulator perfectly supports ARM Android images (Recommended).
*   MuMu Pro (Mac) is optimized for Apple Silicon.
