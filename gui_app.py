"""
Python GUI - Kontrolna tabla za Raspberry Pi Pico
===================================================
Biblioteke: tkinter (ugradjeno), pyserial
Instalacija: pip install pyserial
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import serial
import serial.tools.list_ports
import json
import threading
import time
import math

# ══════════════════════════════════════════════════════════════
#  KONSTANTE I TEME
# ══════════════════════════════════════════════════════════════
BG        = "#0d1117"
BG2       = "#161b22"
BG3       = "#21262d"
BORDER    = "#30363d"
TEXT      = "#e6edf3"
TEXT_DIM  = "#7d8590"
ACCENT    = "#58a6ff"
GREEN_ON  = "#3fb950"
GREEN_OFF = "#1a3a1f"
YELLOW_ON = "#d29922"
YELLOW_OFF= "#3a2f0a"
RED_ON    = "#f85149"
RED_OFF   = "#3a0f0d"


# ══════════════════════════════════════════════════════════════
#  CANVAS WIDGET: SERVO VIZUALIZACIJA
# ══════════════════════════════════════════════════════════════
class ServoCanvas(tk.Canvas):
    def __init__(self, parent, size=180, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG2, highlightthickness=0, **kw)
        self.size = size
        self.cx = size // 2
        self.cy = size // 2 + 10
        self.radius = size // 2 - 20
        self._draw_static()
        self.needle = None
        self.set_angle(0)

    def _draw_static(self):
        r = self.radius
        cx, cy = self.cx, self.cy
        # Luk (180 stepeni - od desno levo)
        self.create_arc(cx - r, cy - r, cx + r, cy + r,
                        start=0, extent=180, style="arc",
                        outline=BORDER, width=3)
        # Oznake stepeni
        for deg in range(0, 181, 30):
            rad = math.radians(180 - deg)
            x1 = cx + (r - 8) * math.cos(rad)
            y1 = cy - (r - 8) * math.sin(rad)
            x2 = cx + r * math.cos(rad)
            y2 = cy - r * math.sin(rad)
            self.create_line(x1, y1, x2, y2, fill=BORDER, width=1)
            # Label
            lx = cx + (r - 22) * math.cos(rad)
            ly = cy - (r - 22) * math.sin(rad)
            self.create_text(lx, ly, text=str(deg),
                             fill=TEXT_DIM, font=("Consolas", 7))
        # Centar krug
        self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8,
                         fill=BG3, outline=ACCENT, width=2)

    def set_angle(self, angle):
        angle = max(0, min(180, angle))
        cx, cy = self.cx, self.cy
        r = self.radius - 12
        rad = math.radians(180 - angle)
        x = cx + r * math.cos(rad)
        y = cy - r * math.sin(rad)
        if self.needle:
            self.delete(self.needle)
            self.delete("needle_tip")
        self.needle = self.create_line(cx, cy, x, y,
                                       fill=ACCENT, width=3)
        self.create_oval(x - 5, y - 5, x + 5, y + 5,
                         fill=ACCENT, outline="", tags="needle_tip")


# ══════════════════════════════════════════════════════════════
#  CANVAS WIDGET: RADAR / UDALJENOST
# ══════════════════════════════════════════════════════════════
class RadarCanvas(tk.Canvas):
    def __init__(self, parent, size=200, max_cm=200, **kw):
        super().__init__(parent, width=size, height=size // 2 + 20,
                         bg=BG2, highlightthickness=0, **kw)
        self.size = size
        self.max_cm = max_cm
        self.cx = size // 2
        self.cy = size // 2
        self._draw_static()
        self.dot = None
        self.set_distance(0)

    def _draw_static(self):
        cx, cy = self.cx, self.cy
        r = self.size // 2 - 10
        colors = ["#1a3a1f", "#1a2a0a", "#3a0f0d"]
        radii  = [r, r * 2 // 3, r // 3]
        # Prstenovi (zeleno, zuto, crveno)
        for c, rad in zip(colors, radii):
            self.create_arc(cx - rad, cy - rad, cx + rad, cy + rad,
                            start=0, extent=180, style="arc",
                            outline=c, width=1)
        # Krac linije
        for deg in range(0, 181, 30):
            rad_angle = math.radians(180 - deg)
            x = cx + r * math.cos(rad_angle)
            y = cy - r * math.sin(rad_angle)
            self.create_line(cx, cy, x, y, fill=BORDER, width=1)
        # Oznake
        labels = ["0", f"{self.max_cm//3}", f"{2*self.max_cm//3}", f"{self.max_cm}cm"]
        for i, (rad, label) in enumerate(zip([0, r//3, r*2//3, r], labels)):
            if i == 0:
                self.create_text(cx + 4, cy + 2, text=label,
                                 fill=TEXT_DIM, font=("Consolas", 7), anchor="w")
            else:
                self.create_text(cx - rad - 3, cy + 2, text=label,
                                 fill=TEXT_DIM, font=("Consolas", 7), anchor="e")

    def set_distance(self, cm):
        cx, cy = self.cx, self.cy
        r = self.size // 2 - 10
        cm = max(0, min(self.max_cm, cm))
        ratio = cm / self.max_cm
        dot_r = int(ratio * r)
        x = cx - dot_r  # Pravo levo za prikaz
        y = cy

        if cm < self.max_cm * 0.15:
            color = RED_ON
        elif cm < self.max_cm * 0.4:
            color = YELLOW_ON
        else:
            color = GREEN_ON

        if self.dot:
            self.delete("radar_dot")
            self.delete("radar_line")

        self.create_line(cx, cy, x, y,
                         fill=color, width=2, tags="radar_line")
        self.create_oval(x - 6, y - 6, x + 6, y + 6,
                         fill=color, outline="", tags="radar_dot")


# ══════════════════════════════════════════════════════════════
#  GLAVNI PROZOR
# ══════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pico Kontrolna Tabla")
        self.configure(bg=BG)
        self.resizable(False, False)

        # Stanje
        self.ser = None
        self.connected = False
        self.manual_mode = tk.BooleanVar(value=False)
        self.servo_angle = tk.IntVar(value=90)
        self.led_green  = tk.BooleanVar(value=False)
        self.led_yellow = tk.BooleanVar(value=False)
        self.led_red    = tk.BooleanVar(value=False)

        # Live podaci
        self.live_distance = 0.0
        self.live_servo    = 0
        self.live_leds     = {"green": False, "yellow": False, "red": False}
        self.live_mode     = "auto"

        self._build_ui()
        self._start_read_thread()

    # ── Gradnja UI ────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=12, pady=8)

        # ── Zaglavlje ─────────────────────────────────────────
        header = tk.Frame(self, bg=BG2, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="◈  PICO SENSOR CONTROL",
                 bg=BG2, fg=ACCENT,
                 font=("Courier New", 16, "bold")).pack(side="left", padx=20)
        self.status_lbl = tk.Label(header, text="● OFFLINE",
                                   bg=BG2, fg=RED_ON,
                                   font=("Courier New", 10, "bold"))
        self.status_lbl.pack(side="right", padx=20)

        # ── Konekcija ─────────────────────────────────────────
        conn_frame = tk.Frame(self, bg=BG3, pady=8, padx=12)
        conn_frame.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(conn_frame, text="PORT:", bg=BG3, fg=TEXT_DIM,
                 font=("Courier New", 9)).pack(side="left")

        self.port_var = tk.StringVar()
        self.port_cb = ttk.Combobox(conn_frame, textvariable=self.port_var,
                                    width=18, state="readonly")
        self.port_cb.pack(side="left", padx=6)
        self._refresh_ports()

        btn_style = dict(bg=BG, fg=ACCENT, activebackground=BORDER,
                         activeforeground=TEXT, relief="flat", cursor="hand2",
                         font=("Courier New", 9, "bold"), padx=10, pady=4)

        tk.Button(conn_frame, text="↺ REFRESH",
                  command=self._refresh_ports, **btn_style).pack(side="left", padx=4)
        self.conn_btn = tk.Button(conn_frame, text="CONNECT",
                                   command=self._toggle_connect, **btn_style)
        self.conn_btn.pack(side="left", padx=4)

        # ── Glavni sadrzaj ────────────────────────────────────
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", padx=10, pady=10)

        # Levo: Live podaci
        left = tk.Frame(main, bg=BG2, padx=14, pady=14,
                        relief="flat", bd=0)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self._build_live_panel(left)

        # Desno: Kontrole
        right = tk.Frame(main, bg=BG2, padx=14, pady=14)
        right.pack(side="left", fill="both", padx=(6, 0))
        self._build_control_panel(right)

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=parent["bg"], fg=TEXT_DIM,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(10, 4))
        sep = tk.Frame(parent, bg=BORDER, height=1)
        sep.pack(fill="x", pady=(0, 8))

    # ── Live panel ────────────────────────────────────────────
    def _build_live_panel(self, parent):
        tk.Label(parent, text="LIVE TELEMETRIJA", bg=parent["bg"],
                 fg=TEXT, font=("Courier New", 11, "bold")).pack(anchor="w")

        # Udaljenost
        self._section(parent, "ULTRAZVUCNI SENZOR")
        dist_row = tk.Frame(parent, bg=parent["bg"])
        dist_row.pack(fill="x")
        self.dist_lbl = tk.Label(dist_row, text="---",
                                  bg=parent["bg"], fg=GREEN_ON,
                                  font=("Courier New", 36, "bold"))
        self.dist_lbl.pack(side="left")
        tk.Label(dist_row, text="cm", bg=parent["bg"], fg=TEXT_DIM,
                 font=("Courier New", 14)).pack(side="left", padx=6, anchor="s", pady=8)

        # Radar vizualizacija
        self.radar = RadarCanvas(parent, size=240, max_cm=200)
        self.radar.pack(pady=6)

        # Servo vizualizacija
        self._section(parent, "SERVO POZICIJA")
        self.servo_canvas = ServoCanvas(parent, size=200)
        self.servo_canvas.pack(pady=4)
        self.servo_live_lbl = tk.Label(parent, text="0°",
                                        bg=parent["bg"], fg=ACCENT,
                                        font=("Courier New", 18, "bold"))
        self.servo_live_lbl.pack()

        # LED status
        self._section(parent, "LED STATUS")
        led_row = tk.Frame(parent, bg=parent["bg"])
        led_row.pack()
        self.live_led_widgets = {}
        for color, label, on_c, off_c in [
            ("green",  "ZELENO",  GREEN_ON,  GREEN_OFF),
            ("yellow", "ZUTO",    YELLOW_ON, YELLOW_OFF),
            ("red",    "CRVENO",  RED_ON,    RED_OFF),
        ]:
            f = tk.Frame(led_row, bg=parent["bg"])
            f.pack(side="left", padx=8)
            dot = tk.Label(f, text="●", bg=parent["bg"], fg=off_c,
                           font=("Courier New", 22))
            dot.pack()
            tk.Label(f, text=label, bg=parent["bg"], fg=TEXT_DIM,
                     font=("Courier New", 7)).pack()
            self.live_led_widgets[color] = (dot, on_c, off_c)

        # Rezim
        self._section(parent, "REZIM")
        self.mode_lbl = tk.Label(parent, text="AUTO", bg=parent["bg"],
                                  fg=GREEN_ON, font=("Courier New", 13, "bold"))
        self.mode_lbl.pack(anchor="w")

    # ── Kontrolni panel ───────────────────────────────────────
    def _build_control_panel(self, parent):
        tk.Label(parent, text="MANUELNA KONTROLA", bg=parent["bg"],
                 fg=TEXT, font=("Courier New", 11, "bold")).pack(anchor="w")

        # Rezim prekidac
        self._section(parent, "REZIM RADA")
        mode_frame = tk.Frame(parent, bg=parent["bg"])
        mode_frame.pack(anchor="w")

        self.auto_rb = tk.Radiobutton(mode_frame, text="AUTO (senzor)",
                                       variable=self.manual_mode, value=False,
                                       bg=parent["bg"], fg=TEXT, selectcolor=BG3,
                                       activebackground=parent["bg"],
                                       font=("Courier New", 10),
                                       command=self._send_mode)
        self.auto_rb.pack(anchor="w")
        self.manual_rb = tk.Radiobutton(mode_frame, text="MANUAL (GUI)",
                                         variable=self.manual_mode, value=True,
                                         bg=parent["bg"], fg=TEXT, selectcolor=BG3,
                                         activebackground=parent["bg"],
                                         font=("Courier New", 10),
                                         command=self._send_mode)
        self.manual_rb.pack(anchor="w")

        # Servo kontrola
        self._section(parent, "SERVO MOTOR")
        angle_frame = tk.Frame(parent, bg=parent["bg"])
        angle_frame.pack(fill="x")

        self.angle_display = tk.Label(angle_frame, text="90°",
                                       bg=BG3, fg=ACCENT,
                                       font=("Courier New", 22, "bold"),
                                       width=6, relief="flat")
        self.angle_display.pack(side="left", padx=(0, 12))

        slider_frame = tk.Frame(angle_frame, bg=parent["bg"])
        slider_frame.pack(side="left", fill="x", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Horizontal.TScale",
                         background=parent["bg"],
                         troughcolor=BG3,
                         sliderthickness=18)

        self.angle_slider = ttk.Scale(slider_frame,
                                       from_=0, to=180,
                                       variable=self.servo_angle,
                                       orient="horizontal",
                                       style="Custom.Horizontal.TScale",
                                       command=self._on_slider)
        self.angle_slider.pack(fill="x", pady=4)

        tick_frame = tk.Frame(slider_frame, bg=parent["bg"])
        tick_frame.pack(fill="x")
        for deg in [0, 45, 90, 135, 180]:
            tk.Label(tick_frame, text=f"{deg}°", bg=parent["bg"], fg=TEXT_DIM,
                     font=("Courier New", 7)).pack(side="left", expand=True)

        # Brze akcije
        btn_row = tk.Frame(parent, bg=parent["bg"])
        btn_row.pack(fill="x", pady=6)
        btn_s = dict(bg=BG3, fg=ACCENT, activebackground=BORDER,
                     activeforeground=TEXT, relief="flat", cursor="hand2",
                     font=("Courier New", 9), padx=8, pady=4)
        for label, val in [("0°", 0), ("45°", 45), ("90°", 90),
                            ("135°", 135), ("180°", 180)]:
            tk.Button(btn_row, text=label,
                      command=lambda v=val: self._set_angle(v),
                      **btn_s).pack(side="left", padx=2)

        # LED kontrola
        self._section(parent, "LED DIODE")
        self.led_btns = {}
        for color, label, on_c, off_c, var in [
            ("green",  "ZELENA  (x2)", GREEN_ON,  GREEN_OFF,  self.led_green),
            ("yellow", "ZUTA    (x2)", YELLOW_ON, YELLOW_OFF, self.led_yellow),
            ("red",    "CRVENA  (x2)", RED_ON,    RED_OFF,    self.led_red),
        ]:
            row = tk.Frame(parent, bg=parent["bg"])
            row.pack(fill="x", pady=3)
            btn = tk.Button(row, text=f"● {label}  OFF",
                            bg=off_c, fg=TEXT, activebackground=on_c,
                            activeforeground=TEXT, relief="flat", cursor="hand2",
                            font=("Courier New", 10, "bold"),
                            width=22, pady=6,
                            command=lambda c=color, v=var: self._toggle_led(c, v))
            btn.pack(side="left")
            self.led_btns[color] = (btn, var, on_c, off_c, label)

        # Sve LED
        all_row = tk.Frame(parent, bg=parent["bg"])
        all_row.pack(fill="x", pady=(8, 4))
        btn_s2 = dict(bg=BG3, fg=TEXT, activebackground=BORDER,
                      activeforeground=TEXT, relief="flat", cursor="hand2",
                      font=("Courier New", 9, "bold"), padx=12, pady=4)
        tk.Button(all_row, text="SVE ON",
                  command=self._all_leds_on, **btn_s2).pack(side="left", padx=4)
        tk.Button(all_row, text="SVE OFF",
                  command=self._all_leds_off, **btn_s2).pack(side="left", padx=4)

    # ── Konekcija ─────────────────────────────────────────────
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb["values"] = ports
        if ports:
            self.port_cb.current(0)

    def _toggle_connect(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            return
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
            self.connected = True
            self.status_lbl.config(text="● ONLINE", fg=GREEN_ON)
            self.conn_btn.config(text="DISCONNECT")
        except Exception as e:
            self.status_lbl.config(text=f"● GRESKA: {e}", fg=RED_ON)

    def _disconnect(self):
        self.connected = False
        if self.ser:
            self.ser.close()
            self.ser = None
        self.status_lbl.config(text="● OFFLINE", fg=RED_ON)
        self.conn_btn.config(text="CONNECT")

    # ── Slanje komandi ────────────────────────────────────────
    def _send(self, data: dict):
        if self.connected and self.ser:
            try:
                self.ser.write((json.dumps(data) + "\n").encode())
            except Exception:
                self._disconnect()

    def _send_mode(self):
        self._send({"type": "mode", "manual": self.manual_mode.get()})

    def _on_slider(self, val):
        angle = int(float(val))
        self.angle_display.config(text=f"{angle}°")
        if self.manual_mode.get():
            self._send({"type": "servo", "angle": angle})

    def _set_angle(self, val):
        self.servo_angle.set(val)
        self.angle_display.config(text=f"{val}°")
        if self.manual_mode.get():
            self._send({"type": "servo", "angle": val})

    def _toggle_led(self, color, var):
        var.set(not var.get())
        btn, v, on_c, off_c, label = self.led_btns[color]
        state = v.get()
        btn.config(bg=on_c if state else off_c,
                   text=f"● {label}  {'ON ' if state else 'OFF'}")
        if self.manual_mode.get():
            self._send({
                "type": "led",
                "green":  self.led_green.get(),
                "yellow": self.led_yellow.get(),
                "red":    self.led_red.get()
            })

    def _all_leds_on(self):
        for color, (btn, var, on_c, off_c, label) in self.led_btns.items():
            var.set(True)
            btn.config(bg=on_c, text=f"● {label}  ON ")
        if self.manual_mode.get():
            self._send({"type": "led", "green": True, "yellow": True, "red": True})

    def _all_leds_off(self):
        for color, (btn, var, on_c, off_c, label) in self.led_btns.items():
            var.set(False)
            btn.config(bg=off_c, text=f"● {label}  OFF")
        if self.manual_mode.get():
            self._send({"type": "led", "green": False, "yellow": False, "red": False})

    # ── Citanje sa Pico-a ─────────────────────────────────────
    def _start_read_thread(self):
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()

    def _read_loop(self):
        while True:
            if self.connected and self.ser:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        data = json.loads(line)
                        self.after(0, lambda d=data: self._update_live(d))
                except Exception:
                    pass
            time.sleep(0.05)

    def _update_live(self, data):
        dist = data.get("distance", 0)
        angle = data.get("servo", 0)
        leds = data.get("leds", {})
        mode = data.get("mode", "auto")

        # Udaljenost
        self.dist_lbl.config(text=f"{dist:.1f}")
        if dist > 0:
            if dist < 15:
                self.dist_lbl.config(fg=RED_ON)
            elif dist < 40:
                self.dist_lbl.config(fg=YELLOW_ON)
            else:
                self.dist_lbl.config(fg=GREEN_ON)

        # Radar
        self.radar.set_distance(dist)

        # Servo vizualizacija
        self.servo_canvas.set_angle(angle)
        self.servo_live_lbl.config(text=f"{angle}°")

        # LED vizualizacija
        for color, (dot, on_c, off_c) in self.live_led_widgets.items():
            dot.config(fg=on_c if leds.get(color) else off_c)

        # Rezim
        if mode == "manual":
            self.mode_lbl.config(text="MANUAL", fg=ACCENT)
        else:
            self.mode_lbl.config(text="AUTO", fg=GREEN_ON)


# ══════════════════════════════════════════════════════════════
#  POKRETANJE
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
