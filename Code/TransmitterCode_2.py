from machine import Pin, PWM, I2C
import socket
import network
import time
import math
import gc
import neopixel
import ujson

gc.collect()

# ----------- Hardware Setup -------------- #

# Buzzer
buzzer = PWM(Pin(15))
BASE_FREQ = 500
buzzer.freq(BASE_FREQ)

# NeoPixel
NUM_LEDS = 8
np = neopixel.NeoPixel(Pin(18), NUM_LEDS)

# ----------- MPU6050 Setup -------------- #

sda = Pin(4, Pin.IN, Pin.PULL_UP)
scl = Pin(5, Pin.IN, Pin.PULL_UP)
i2c = I2C(0, sda=sda, scl=scl, freq=200000)
MPU_ADDR = 0x68
GYRO_Z = 0x47

print("I2C Devices:", i2c.scan())

# Wake MPU6050
i2c.writeto(MPU_ADDR, b'\x6B\x00')
time.sleep_ms(100)

# ----------- Distance + Sound Settings -------------- #

MAX_DISTANCE = 5
MAX_DUTY = 65535

BEEP_DURATION_MS = 80
MIN_INTERVAL = 200
MAX_INTERVAL = 2000
last_beep_time = time.ticks_ms()

# ----------- Helper Functions -------------- #

def read_gyro_z():
    i2c.writeto(MPU_ADDR, bytes([GYRO_Z]))
    high = i2c.readfrom(MPU_ADDR, 1)[0]
    i2c.writeto(MPU_ADDR, bytes([GYRO_Z + 1]))
    low = i2c.readfrom(MPU_ADDR, 1)[0]

    gz_raw = (high << 8) | low
    if gz_raw > 32767:
        gz_raw -= 65536

    return gz_raw / 131.0  # deg/sec


def update_buzzer_frequency(gz):
    # Clamp rotation to reasonable range
    max_rotation = 200
    if gz > max_rotation:
        gz = max_rotation
    if gz < -max_rotation:
        gz = -max_rotation

    # Map rotation magnitude to frequency shift
    freq_shift = int(abs(gz) * 5)
    buzzer.freq(BASE_FREQ + freq_shift)


def clamp_distance(distance):
    if distance == float('inf'):
        return MAX_DISTANCE
    if distance < 0:
        return 0
    if distance > MAX_DISTANCE:
        return MAX_DISTANCE
    return distance


def duty_from_distance(distance):
    distance = clamp_distance(distance)
    return int((distance / MAX_DISTANCE) * MAX_DUTY)


def interval_from_distance(distance):
    distance = clamp_distance(distance)
    ratio = distance / MAX_DISTANCE
    return int(MIN_INTERVAL + (ratio * (MAX_INTERVAL - MIN_INTERVAL)))


def leds_from_distance(distance):
    distance = clamp_distance(distance)

    ratio = 1 - (distance / MAX_DISTANCE)
    led_count = math.ceil(ratio * NUM_LEDS)

    np.fill((0, 0, 0))

    for i in range(led_count):
        r = led_count * 30
        b = 225 - (led_count * 10)
        g = 0
        np[i] = (r, g, b)

    np.write()


def beep(duty):
    buzzer.duty_u16(duty)
    time.sleep_ms(BEEP_DURATION_MS)
    buzzer.duty_u16(0)




# Start AP mode (SSID="hello")
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="hello", password="password")  # No password if open
print("AP IP:", ap.ifconfig()[0])  # Usually 192.168.4.1 [web:46]


try:
    # UDP server on AP
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind(("0.0.0.0", 12345))  # Bind all interfaces, port 12345
  print("Listening for UDP on port 12345")
  
  while True:

    # ----------------------------- GET DISTANCE ---------------------------------------
    data, client_addr = sock.recvfrom(1024)

    info = ujson.loads(data)  # → {"dist":1.8}
    distance = info["dist"]       # float
    # print(f"From {client_addr}: DIST={distance}")


    # --------------------------------------------------------------
    duty = duty_from_distance(distance)
    interval = interval_from_distance(distance)

    leds_from_distance(distance)

  
    # --- Gyro ---
    gz = read_gyro_z()
    update_buzzer_frequency(gz)

    print("Distance:", distance, "| Gyro Z:", gz)

    now = time.ticks_ms()
    if time.ticks_diff(now, last_beep_time) >= interval:
        beep(duty)
        last_beep_time = now

    
  #____________________________________________________
    time.sleep_ms(100)

finally:
  print("closing Socket")
  sock.close()
  buzzer.duty_u16(0)
  buzzer.deinit()

  np.fill((0, 0, 0))
  np.write()

  print("All systems shut down.")