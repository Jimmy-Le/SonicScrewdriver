# -------- Imports --------
import board
import time
import math
import gc
import json
import neopixel
import socketpool
import wifi
import pwmio
import adafruit_mpu6050

# -------- Garbage Collection --------
gc.collect()

# -------- PWM Audio --------
speaker = pwmio.PWMOut(board.A0, duty_cycle=0, frequency=440, variable_frequency=True)

# -------- Melody --------
base_volume = 0.02
volumeModifier = 1
bendBy = 0
durationMultiplier = 1

melody = [
    (60, 0.25, base_volume),
    (60, 0.25, base_volume),
    (64, 0.25, base_volume),
    (64, 0.25, base_volume),
    (57, 0.25, base_volume),
    (57, 0.25, base_volume),
    (60, 0.25, base_volume),
    (60, 0.25, base_volume),
    (62, 0.25, base_volume),
    (62, 0.25, base_volume),
    (65, 0.25, base_volume),
    (65, 0.25, base_volume),
    (55, 0.25, base_volume),
    (55, 0.25, base_volume),
    (59, 0.25, base_volume),
    (59, 0.25, base_volume)
]

currentNote = 0
melodyLength = len(melody)

# -------- NeoPixels --------
NUM_LEDS = 8
np = neopixel.NeoPixel(board.A2, NUM_LEDS, brightness=0.1)

# -------- MPU6050 --------
i2c = board.I2C()
mpu = adafruit_mpu6050.MPU6050(i2c)

# -------- Distance + Timing --------
MAX_DISTANCE = 2
MIN_INTERVAL = 200
MAX_INTERVAL = 2000
last_beep_time = time.monotonic()

# -------- WiFi --------
TARGET_SSID = "hello"
PASSWORD = "password"
PORT = 12345

# -------- Helpers --------
def midi_to_hz(m):
    return 440 * (2 ** ((m - 69) / 12))


def clamp_distance(distance):
    if distance == float("inf"):
        return MAX_DISTANCE
    return max(0, min(distance, MAX_DISTANCE))


def interval_from_distance(distance):
    ratio = clamp_distance(distance) / MAX_DISTANCE
    return int(MIN_INTERVAL + (ratio * (MAX_INTERVAL - MIN_INTERVAL)))


def leds_from_distance(distance):
    ratio = 1 - (clamp_distance(distance) / MAX_DISTANCE)
    led_count = math.ceil(ratio * NUM_LEDS)

    np.fill((0, 0, 0))
    for i in range(led_count):
        r = i * 50
        g = 0
        b = 100 - (i * 25)

        r = min(255, max(0, r))
        b = min(255, max(0, b))
        np[i] = (r, g, b)
    np.show()


def read_gyro_z():
    gz = mpu.gyro[2] * (180 / math.pi)
    print(f"Gyro Z: {gz:.2f}")
    return gz


# -------- PWM Audio --------
def playNote():
    global currentNote

    midi_note, duration, vol = melody[currentNote]
    vol *= volumeModifier
    duration *= durationMultiplier

    if midi_note == 0:
        speaker.duty_cycle = 0
        time.sleep(duration)
    else:
        freq = midi_to_hz(midi_note)

        # Apply pitch bend (adjust frequency)
        freq = freq * (1 + bendBy)

        speaker.frequency = int(freq)
        speaker.duty_cycle = int(65535 * vol)

        time.sleep(duration)
        speaker.duty_cycle = 0
    time.sleep(0.05)
    currentNote = (currentNote + 1) % melodyLength


def update_audio(gz, distance):
    global bendBy, volumeModifier, durationMultiplier

    max_rotation = 200
    gz = max(min(gz, max_rotation), -max_rotation)
    howFar = 1 / (clamp_distance(distance))

    # Pitch bend
    bendBy = gz * 0.003

    # Volume from distance
    dist = clamp_distance(distance)
    if dist == 0:
        volumeModifier = 1
        durationMultiplier = 1
    else:
        volumeModifier = max(0.01, min(1 / dist, 1))
        durationMultiplier = max(0.75, min(dist, 1.25))
    playNote()


def reconnect_wifi(timeout=10):
    print("Reconnecting WiFi...")

    try:
        wlan.disconnect()
    except:
        pass
    try:
        wlan.connect(TARGET_SSID, PASSWORD)
    except Exception as e:
        print("Connect error:", e)
        return False
    start = time.monotonic()
    while not wlan.ipv4_address:
        if time.monotonic() - start > timeout:
            print("WiFi reconnect timeout")
            return False
        time.sleep(0.5)
    print("Reconnected! IP:", wlan.ipv4_address)
    return True


# -------- RSSI â†’ Distance --------
def rssi_to_distance(rssi, P0=-50, n=2.5):
    if rssi == 0:
        return float("inf")
    return 10 ** ((P0 - rssi) / (10 * n))


def get_connected_rssi(ssid):
    aps = wifi.radio.start_scanning_networks()
    rssi = -50
    for ap in aps:
        if ap.ssid == ssid:
            rssi = ap.rssi
            break
    wifi.radio.stop_scanning_networks()
    return rssi


# -------- WiFi Setup --------
wlan = wifi.radio
wlan.stop_ap()
time.sleep(1)

print("Connecting to WiFi...")
wlan.connect(TARGET_SSID, PASSWORD)

while not wlan.ipv4_address:
    print("Connecting...")
    time.sleep(1)
print("Connected! IP:", wlan.ipv4_address)

pool = socketpool.SocketPool(wlan)
sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

# -------- Main Loop --------
try:
    while True:
        rssi = get_connected_rssi(TARGET_SSID)
        distance = rssi_to_distance(rssi)
        leds_from_distance(distance)
        gz = read_gyro_z()
        message = json.dumps({
            "dist": distance,
            "gyro": gz
        }).encode()
        try:
            sock.sendto(message, ("192.168.4.1", PORT))
        except OSError as e:
            print("Socket error:", e)

            try:
                sock.close()
            except:
                pass
            # Ensure WiFi is still connected
            if not wlan.ipv4_address:
                if not reconnect_wifi():
                    time.sleep(1)
                    continue
            # Recreate socket
            try:
                pool = socketpool.SocketPool(wlan)
                sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
                print("Socket recreated")
            except Exception as e:
                print("Socket recreation failed:", e)
            continue
        print(f"RSSI: {rssi} | Distance: {distance}")



        now = time.monotonic()
        interval = interval_from_distance(distance) / 1000

        if (now - last_beep_time) >= interval:
            update_audio(gz, distance)
            last_beep_time = now
        time.sleep(0.05)
finally:
    try:
        sock.close()
    except:
        pass
    try:
        speaker.duty_cycle = 0
    except:
        pass
    try:
        np.fill((0, 0, 0))
        np.show()
    except:
        pass
    print("Shutdown complete.")
