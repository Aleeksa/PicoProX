# 🛰️ PicoProx - Proximity Control System

**PicoProx** is an advanced proximity monitoring and control system built on the **Raspberry Pi Pico** platform. It utilizes ultrasonic technology for real-time object detection and features a dedicated Python Dashboard for remote monitoring and manual override.

---

## 🛠️ Key Features

### 🤖 Hardware Automation
* **Smart Detection:** Real-time distance tracking using the HC-SR04 ultrasonic sensor.
* **Dynamic Servo Response:** The servo motor rotates proportionally to the object's proximity (simulating a barrier or valve).
* **LED Traffic Light:** Visual signaling through three stages:
    * **Green:** Safe distance
    * **Yellow:** Warning zone
    * **Red:** Critical proximity

### 💻 Python GUI Dashboard
* **Live Monitoring:** Digital display showing the measured distance in meters (m).
* **Manual Override:** Integrated slider to manually adjust the servo motor angle.
* **LED Manager:** Digital switches to toggle each LED color (Green, Yellow, Red) independently.
* **Seamless Connectivity:** Communication handled via Serial (UART) protocol.

---

## 🔧 Components

| Component | Purpose |
|---|---|
| **Raspberry Pi Pico** | Main controller (programmed in MicroPython) |
| **HC-SR04** | Ultrasonic sensor for distance measurement |
| **SG90 Servo** | Actuator for mechanical movement |
| **LED Diodes** | 2x Green, 2x Yellow, 2x Red indicators |
| **Python (Tkinter)** | Graphical User Interface for desktop control |

---

## 📂 Project Structure

* `pico_main.py` - MicroPython source code for the Raspberry Pi Pico.
* `gui_app.py` - Python source code for the desktop GUI.
* `requirements.txt` - Required Python libraries (e.g., `pyserial`).

---

## 🚀 Getting Started

1.  **Flash the Pico:** Upload `pico_main.py` to your Raspberry Pi Pico using Thonny IDE.
2.  **Hardware Setup:** Connect the sensors, servo, and LEDs according to the wiring diagram.
3.  **Run the Dashboard:** Install dependencies via `pip install pyserial` and launch `dashboard_app.py` on your computer.

---

**Author:** [Your Name]  
**Project:** PicoProx Proximity Control System for Raspberry Pi Pico
