"""
Raspberry Pi Pico - Ultrazvucni senzor + LED + Servo Motor
=============================================================
Pinout:
  - Ultrazvucni senzor TRIG -> GP14
  - Ultrazvucni senzor ECHO -> GP15
  - LED Zelena 1 -> GP2
  - LED Zelena 2 -> GP3
  - LED Zuta 1  -> GP4
  - LED Zuta 2  -> GP5
  - LED Crvena 1 -> GP6
  - LED Crvena 2 -> GP7
  - Servo Motor  -> GP9 (PWM)
  - UART TX (ka PC-u) -> GP0
  - UART RX (od PC-a) -> GP1
"""

from machine import Pin, PWM, UART, time_pulse_us
import time
import json

# ── UART komunikacija sa Python GUI ──────────────────────────
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

# ── Ultrazvucni senzor ────────────────────────────────────────
TRIG = Pin(14, Pin.OUT)
ECHO = Pin(15, Pin.IN)

# ── LED diode ─────────────────────────────────────────────────
led_green1  = Pin(2, Pin.OUT)
led_green2  = Pin(3, Pin.OUT)
led_yellow1 = Pin(4, Pin.OUT)
led_yellow2 = Pin(5, Pin.OUT)
led_red1    = Pin(6, Pin.OUT)
led_red2    = Pin(7, Pin.OUT)

all_leds = [led_green1, led_green2, led_yellow1, led_yellow2, led_red1, led_red2]

# ── Servo Motor (PWM na GP9) ──────────────────────────────────
servo_pwm = PWM(Pin(9))
servo_pwm.freq(50)  # 50Hz standardno za servo

# Servo pomocne funkcije
def angle_to_duty(angle):
    """Konvertuje ugao (0-180) u duty cycle za servo (500-2500 us)"""
    min_us = 500
    max_us = 2500
    us = min_us + (max_us - min_us) * angle / 180
    duty = int(us / 20000 * 65535)
    return duty

def set_servo(angle):
    angle = max(0, min(180, angle))
    servo_pwm.duty_u16(angle_to_duty(angle))

# ── Merjenje udaljenosti ──────────────────────────────────────
def measure_distance_cm():
    """Vraca udaljenost u cm. -1 ako nema odgovora."""
    TRIG.low()
    time.sleep_us(2)
    TRIG.high()
    time.sleep_us(10)
    TRIG.low()
    
    duration = time_pulse_us(ECHO, 1, 30000)  # timeout 30ms (~5m)
    if duration < 0:
        return -1.0
    return (duration / 2) / 29.1  # cm

# ── LED logika na osnovu distance ─────────────────────────────
def leds_off():
    for led in all_leds:
        led.low()

def set_leds_by_distance(distance_cm):
    leds_off()
    if distance_cm < 0:
        return  # nema merenja
    if distance_cm < 15:
        # Crveno - opasna blizina
        led_red1.high()
        led_red2.high()
    elif distance_cm < 40:
        # Zuto - srednja blizina
        led_yellow1.high()
        led_yellow2.high()
    else:
        # Zeleno - daleko / bezbedno
        led_green1.high()
        led_green2.high()

def distance_to_servo_angle(distance_cm):
    """
    Sto blize, veci ugao (do 180).
    Sto dalje, manji ugao (do 0).
    Radi u opsegu 5 - 80 cm.
    """
    min_dist = 5.0
    max_dist = 80.0
    distance_cm = max(min_dist, min(max_dist, distance_cm))
    # Inverzno: blize = veci ugao
    angle = 180 - int((distance_cm - min_dist) / (max_dist - min_dist) * 180)
    return angle

# ── Stanja upravljanja ─────────────────────────────────────────
manual_mode = False          # True = GUI kontrolise, False = auto
manual_servo_angle = 90
manual_leds = {
    "green": False,
    "yellow": False,
    "red": False
}

def apply_manual_leds():
    leds_off()
    if manual_leds["green"]:
        led_green1.high()
        led_green2.high()
    if manual_leds["yellow"]:
        led_yellow1.high()
        led_yellow2.high()
    if manual_leds["red"]:
        led_red1.high()
        led_red2.high()

# ── Citanje komandi od GUI-ja ──────────────────────────────────
def read_uart_command():
    global manual_mode, manual_servo_angle, manual_leds
    if uart.any():
        try:
            raw = uart.readline()
            if raw:
                line = raw.decode('utf-8').strip()
                cmd = json.loads(line)
                
                if cmd.get("type") == "mode":
                    manual_mode = cmd.get("manual", False)
                
                elif cmd.get("type") == "servo":
                    manual_servo_angle = int(cmd.get("angle", 90))
                    if manual_mode:
                        set_servo(manual_servo_angle)
                
                elif cmd.get("type") == "led":
                    manual_leds["green"]  = cmd.get("green", False)
                    manual_leds["yellow"] = cmd.get("yellow", False)
                    manual_leds["red"]    = cmd.get("red", False)
                    if manual_mode:
                        apply_manual_leds()

        except Exception as e:
            pass  # Ignorisi lose poruke

# ── Slanje podataka GUI-ju ─────────────────────────────────────
def send_status(distance_cm, servo_angle, leds_state):
    data = {
        "distance": round(distance_cm, 1),
        "servo": servo_angle,
        "leds": leds_state,
        "mode": "manual" if manual_mode else "auto"
    }
    uart.write(json.dumps(data) + "\n")

# ── Glavni loop ───────────────────────────────────────────────
print("Pico spreman. Pokrecanje petlje...")
set_servo(0)  # Pocetni polozaj
time.sleep(1)

last_send = time.ticks_ms()
SEND_INTERVAL = 100  # ms

while True:
    read_uart_command()
    
    distance = measure_distance_cm()
    
    if manual_mode:
        set_servo(manual_servo_angle)
        apply_manual_leds()
        current_angle = manual_servo_angle
        current_leds = {k: v for k, v in manual_leds.items()}
    else:
        if distance > 0:
            angle = distance_to_servo_angle(distance)
            set_servo(angle)
            set_leds_by_distance(distance)
            current_angle = angle
        else:
            current_angle = 0
        current_leds = {
            "green":  distance >= 40,
            "yellow": 15 <= distance < 40,
            "red":    0 < distance < 15
        }
    
    # Salji status svakih 100ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_send) >= SEND_INTERVAL:
        send_status(distance if distance > 0 else 0.0, current_angle, current_leds)
        last_send = now
    
    time.sleep_ms(50)
