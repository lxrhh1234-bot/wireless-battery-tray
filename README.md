# 2.4GHz & Bluetooth Wireless Battery Tray

[中文说明](#中文说明) | [English](#english)

---

## 中文说明

一个轻量级的 Windows 系统托盘工具，无需安装臃肿的厂商驱动软件，直接通过 Windows 原生 HID 与 PnP 接口实时读取 **2.4GHz 无线外设** 和 **蓝牙设备** 的电量与充电状态。

### 功能特点

- **零额外驱动/蓝牙库依赖**：基于 Python 标准库 `ctypes` 调用 `setupapi.dll` / `hid.dll` 与 `Shell_NotifyIconW`，仅需 `Pillow` 绘制托盘图标。
- **2.4GHz + 蓝牙双支持**：既支持 2.4GHz 接收器私有 HID 协议，也支持通过 Windows PnP 属性自动发现并读取所有**已连接**蓝牙设备（耳机、键鼠、Xbox 手柄等）的电量。
- **极简白色卡片界面**：左键点击托盘图标，在图标正上方弹出紧凑的白色电量卡片，支持点击即刷新、休眠状态保留上次电量。
- **低电量桌面提醒**：设备电量低于设定阈值（默认 `20%`）时发送一次 Windows 系统通知提醒，避免断电。
- **低资源占用 & 单实例防重开**：后台按间隔轮询（默认 30 秒），平时几乎不占用 CPU；内置互斥锁防止重复启动多个托盘图标。
- **可自定义设置**：支持自定义设备别名、隐藏未连接接收器的设备、开关蓝牙设备显示、调整刷新间隔以及开机自动启动。

### 目前支持设备

| 设备 | VID / PID / 协议 | 通信方式 |
| :--- | :--- | :--- |
| **ASUS ROG PELTA (2.4GHz)** 无线耳机 | `0B05:1B84` | HID Output/Input Report (`0xCC 0x12 0x07`) |
| **MCHOSE A7 Pro** 无线鼠标 | `5253:1021` | HID Feature Report (`0x11`) |
| **Compx 2.4G 无线接收器**（如 AULA F75 / 迈从 / LEOBOG 等键盘） | `3554:FA09` | HID Output/Input Report (`0x13 0x05`) |
| **Windows 已连接蓝牙设备**（耳机、键鼠、Xbox 手柄等） | 标准 Windows 蓝牙电量服务 | PnP `DEVPKEY_Device_BatteryPlusCharging` |

> 你可以在 `hid_devices.py` 中参照现有轮询函数并添加到 `DEVICE_DEFINITIONS`，轻松扩展更多 2.4GHz 设备。

### 快速开始

1. **环境要求**：Windows 10 / Windows 11，Python 3.10+
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **运行程序**：双击 **`start_tray.bat`** 即可无黑框静默启动（或运行 `pythonw tray_app.py`）。
   - **左键点击托盘图标**：打开/关闭电量卡片并立即刷新一次
   - **右键点击托盘图标**：打开菜单（查看电量 / 立即刷新 / 设置 / 退出）

---

## English

A lightweight Windows system tray utility to monitor battery levels and charging status of **2.4GHz wireless peripherals** and **Bluetooth devices** in real time—without installing heavy vendor software.

### Features

- **Minimal Dependencies**: Uses Python's built-in `ctypes` (`setupapi.dll`, `hid.dll`, `Shell_NotifyIconW`) and `Tkinter`, requiring only `Pillow` for tray icon rendering.
- **2.4GHz + Bluetooth Support**: Reads battery telemetry from vendor-specific 2.4GHz HID protocols as well as all **currently connected** Windows Bluetooth devices (headsets, mice, keyboards, Xbox controllers, etc.) via Windows PnP properties.
- **Minimalist Light Flyout**: Left-clicking the tray icon opens a compact white card directly above the icon and immediately refreshes battery readings, while preserving last-known levels when devices sleep.
- **Low-Battery Notifications**: Sends a one-time Windows toast notification when a discharging device drops below the configured threshold (default `20%`).
- **Low Overhead & Single Instance**: Polls in the background at a configurable interval (default `30s`) with near-zero idle CPU usage, protected by a Windows mutex against duplicate instances.
- **Customizable Settings**: Custom device aliases, hide disconnected receivers, toggle Bluetooth monitoring, configurable polling interval, and run-on-startup support.

### Supported Devices

| Device | VID / PID / Protocol | Transport |
| :--- | :--- | :--- |
| **ASUS ROG PELTA (2.4GHz)** Headset | `0B05:1B84` | HID Output/Input Report (`0xCC 0x12 0x07`) |
| **MCHOSE A7 Pro** Wireless Mouse | `5253:1021` | HID Feature Report (`0x11`) |
| **Compx 2.4G Wireless Receiver** (e.g., AULA F75 / MCHOSE / LEOBOG keyboards) | `3554:FA09` | HID Output/Input Report (`0x13 0x05`) |
| **Connected Windows Bluetooth Devices** | Standard Windows BT Battery | PnP `DEVPKEY_Device_BatteryPlusCharging` |

> You can easily add more 2.4GHz devices by implementing a polling function in `hid_devices.py` and registering it in `DEVICE_DEFINITIONS`.

### Quick Start

1. **Requirements**: Windows 10 / Windows 11, Python 3.10+
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run**: Double-click **`start_tray.bat`** to launch silently without a console window (or run `pythonw tray_app.py`).
   - **Left-click tray icon**: Toggle the battery flyout and trigger an immediate refresh
   - **Right-click tray icon**: Open menu (View Battery / Refresh / Settings / Exit)

---

## Project Structure / 项目结构

```text
wireless-battery-tray/
├── tray_app.py       # Tray icon, single-instance mutex, polling & low-battery alerts
├── ui_windows.py     # Minimalist white flyout card & settings window (Tkinter)
├── hid_devices.py    # Windows HID protocols & Bluetooth PnP battery reader
├── config.py         # Local configuration persistence (config.json)
├── start_tray.bat    # Silent launcher without console window
├── requirements.txt  # Python dependencies
├── .gitignore        # Git ignore rules
└── LICENSE           # MIT License
```

## License

[MIT](LICENSE)
