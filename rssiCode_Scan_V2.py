from machine import Pin, PWM, I2C
import socket
import network
import time
import math
import gc
import neopixel
import ujson

gc.collect()

rssi = 0;

# ----------- Hardware Setup -------------- #

# Buzzer
buzzer = PWM(Pin(15))
BASE_FREQ = 800
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
        r = 250 - (led_count * 25)
        g = led_count * 25
        np[i] = (r, g, 0)

    np.write()


def beep(duty):
    buzzer.duty_u16(duty)
    time.sleep_ms(BEEP_DURATION_MS)
    buzzer.duty_u16(0)

def rssi_to_distance(rssi, P0=-50, n=2.5):
    if rssi == 0:
        return float('inf')
    return 10 ** ((P0 - rssi) / (10 * n))

try:
  wlan = network.WLAN(network.STA_IF)  # Client/STA mode
  wlan.active(True)
  
  wlan.active(False)
  wlan.disconnect()  # Clears saved creds
  wlan.deinit()      # Resets WiFi chip (Pico W specific)

  wlan.active(True)  # Fresh start

  
  # Scan + connect to "hello" AP
  aps = wlan.scan()
  target_ap = None
  for ap in aps:
      if ap[0] == b"hello":
          target_ap = ap
          break
  
  if not target_ap:
      print("AP 'hello' not found")
      
  
  print("Connecting to hello AP...")
  wlan.connect("hello", "password")  # Replace password
  while not wlan.isconnected():
      print("Connecting...", end=" ")
      time.sleep(1)
  
  print("Connected! IP:", wlan.ifconfig()[0])


  # Send UDP to AP (always 192.168.4.1)
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  # message = f"RSSI: {rssi}".encode()
  message = ujson.dumps({"dist":rssi}).encode()
  # message = b"RSSI: {rssi}"

  last_beep_time = time.ticks_ms()
  
  while True:
      rssi = wlan.status('rssi')  # Bonus: current connection RSSI
      distance = rssi_to_distance(rssi)
      # message = f"RSSI: {distance}".encode()
      message = ujson.dumps({"dist":distance}).encode()
      sock.sendto(message, ("192.168.4.1", 12345))
      print("Sent UDP to AP")
      print(f"RSSI: {rssi}")

    #____________________________________________________
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
      # print(f'Time_Int: {time.ticks_diff(now, last_beep_time)}')
      # print(f'Interval: {interval}')

      
    #____________________________________________________
      time.sleep_ms(100)

finally:
  sock.close()
  buzzer.duty_u16(0)
  buzzer.deinit()

  np.fill((0, 0, 0))
  np.write()

  print("All systems shut down.")

client_send_udp()