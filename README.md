# Mecanum Bot - MicroPython Controller

This project controls a Mecanum-wheeled robot using a Raspberry Pi Pico WH. It supports **Dual-Mode Control** (WiFi/HTTP and Bluetooth Low Energy) and features an **OTA Update System with Safe Boot logic**.

## Features
- **Dual Control**: 
  - **HTTP**: Web interface for control over WiFi.
  - **BLE**: Bluetooth Low Energy control via mobile app (Service: `MecanumBot`).
- **Omnidirectional Movement**: Forward, Backward, Strafe Left/Right, Diagonals, and Spins.
- **OTA Updates**: Over-The-Air firmware updates from GitHub.
- **Safe Boot (Rollback)**: Automatically reverts to the last working version if a bad update causes a crash on boot.

## Architecture
- **`main.py`**: **Supervisor**. Checks if `app.py` runs successfully. If it crashes, it restores `backup.py`.
- **`app.py`**: **Firmware**. The core robot logic, motor control, and server.
- **`ble_uart.py` & `ble_advertising.py`**: BLE helper libraries.

## BLE Command Protocol
Connect to device **MecanumBot**.

| Char | Action |
| :--- | :--- |
| `F` | Forward |
| `B` | Backward |
| `L` | Spin Left |
| `R` | Spin Right |
| `G` | Forward Left Diag |
| `H` | Forward Right Diag |
| `I` | Backward Left Diag |
| `J` | Backward Right Diag |
| `S` | Stop |
| `Y` | Magic Mode |
| `U` | Headlights ON |
| `u` | Headlights OFF |

## Installation
1. Flash `main.py` (Supervisor), `app.py` (Logic), `ble_advertising.py`, and `ble_uart.py` to your Pico WH.
2. Edit `app.py` variables `SSID` and `PASSWORD` with your WiFi credentials.
