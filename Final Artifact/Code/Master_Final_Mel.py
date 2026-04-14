import board
import time
import math
import gc
import json
import neopixel
import socketpool
import wifi
import busio
import adafruit_mpu6050
import audiocore
import audiobusio
import array
import synthio

# -------- Garbage Collection and Debug -------
gc.collect()
print(dir(board))

# -------- Hardware Setup --------

# Audio (I2S) Setup
sample_rate = 8000
audio = audiobusio.I2SOut(
    bit_clock=board.A0,
    word_select=board.A1,
    data=board.A3
)

current_wave = None
BASE_FREQ = 500  # base tone frequency in Hz
BEEP_DURATION_MS = 80

# Melody Setup (Master)
volume = 0.035
volumeModifier = 1
durationMultiplier = 1

env = synthio.Envelope(
    sustain_level=0.02,  # ← this holds down the note
)

synth = synthio.Synthesizer(sample_rate=44100, envelope = env)
audio.play(synth)

melody = [
    (72, 0.5, volume),
    (72, 0.5, volume),
    (72, 0.5, volume),
    (0, 0.5, 0),
    (72, 0.25, volume),
    (71, 0.25, volume),
    (69, 0.25, volume),
    (71, 0.25, volume),
    (72, 0.25, volume),
    (74, 0.5, volume),
    (76, 0.5, volume),
    (76, 0.5, volume),
    (76, 0.5, volume),
    (0, 0.5, 0),
    (76, 0.25, volume),
    (74, 0.25, volume),
    (72, 0.25, volume),
    (74, 0.25, volume),
    (76, 0.25, volume),
    (77, 0.5, volume),
    (79, 1, volume),
    (72, 1, volume),
]

bendBy = 0;
currentNote = 0;
melodyLength = len(melody)

# Neopixel LEDS
NUM_LEDS = 8
np = neopixel.NeoPixel(board.A2, NUM_LEDS, brightness=0.1)

# MPU6050 Setup
#i2c = board.I2C()
#mpu = adafruit_mpu6050.MPU6050(i2c)

# ----------- Distance + Timing Settings --------------
MAX_DISTANCE = 2
MIN_INTERVAL = 200
MAX_INTERVAL = 2000
last_beep_time = time.monotonic()

# ----------- Helper Functions -------------------

def read_gyro_z():
    print(f"Gyro X:{mpu.gyro[0]:.2f}, Y: {mpu.gyro[1]:.2f}, Z: {mpu.gyro[2]:.2f} rad/s")
    return mpu.gyro[2]

def clamp_distance(distance):
    if distance == float('inf'):
        return MAX_DISTANCE
    if distance < 0:
        return 0
    if distance > MAX_DISTANCE:
        return MAX_DISTANCE
    return distance

def interval_from_distance(distance):
    distance = clamp_distance(distance)
    ratio = distance / MAX_DISTANCE
    return int(MIN_INTERVAL + (ratio * (MAX_INTERVAL - MIN_INTERVAL)))

def leds_from_distance(distance):
    distance = clamp_distance(distance)
    ratio = 1 - (distance / MAX_DISTANCE)
    led_count = math.ceil(ratio * NUM_LEDS)

    np.fill((0, 0, 0))

    den = max(1, led_count - 1)

    for i in range(led_count):
        t = i / den

        r = int(255 - (127 * t))
        g = int(255 * (1 - t))
        b = int(128 * t)

        np[i] = (r, g, b)

    np.show()

# ---------- Audio Functions -------------

def make_wave(frequency, volume):
    """Generate a RawSample tone at given frequency and volume (0.0–1.0)"""
    length = sample_rate // frequency
    samples = array.array("H", [
        int(32768 + int(32767 * volume) * math.sin(2 * math.pi * i / length))
        for i in range(length)
    ])
    return audiocore.RawSample(samples, sample_rate=sample_rate)

def update_audioOld(gz, distance):
    """Update tone frequency based on gyro Z and volume based on distance"""
    global current_wave
    max_rotation = 200
    gz = max(min(gz, max_rotation), -max_rotation)
    freq = BASE_FREQ + int(abs(gz) * 1)
    volume = clamp_distance(distance) / MAX_DISTANCE
    volume *= 0.1  # make quieter
    current_wave = make_wave(freq, volume),

def playNote():
    global currentNote
    midi_note, duration, newVolume = melody[currentNote]
    newVolume = newVolume * volumeModifier
    duration = duration * durationMultiplier
    #print(newVolume)

    note = synthio.Note( frequency=synthio.midi_to_hz(midi_note), amplitude= newVolume)
    note.bend = bendBy
    synth.press(note)
    time.sleep(duration)
    synth.release(note)
    time.sleep(0.05)
    currentNote = (currentNote + 1) % melodyLength

def update_audio(gz, distance):
    global bendBy
    global volumeModifier
    global durationMultiplier
    max_rotation = 200
    gz = max(min(gz, max_rotation), -max_rotation)
    bendBy = abs(gz) * 0.005                                                         # This will bend the note by a certain amount

    # Volume from distance
    dist = clamp_distance(distance)
    if dist == 0:
        volumeModifier = 1
        durationMultiplier = 1
    else:
        volumeModifier = max(0.01, min(1 / dist, 1))
        durationMultiplier = max(0.75, min(dist, 1.25))

    playNote()




def beep():
    """Play the current tone once for BEEP_DURATION_MS"""
    if current_wave:
        audio.play(current_wave, loop=True)
        time.sleep(BEEP_DURATION_MS / 1000)
        audio.stop()

# -------------- Access Point Code ----------------
AP_SSID = "hello"
AP_PASSWORD = "password"
PORT = 12345

print("Starting access point...")
wifi.radio.start_ap(ssid=AP_SSID, password=AP_PASSWORD)
print("AP IP:", wifi.radio.ipv4_address_ap)

try:
    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    sock.bind((str(wifi.radio.ipv4_address_ap), PORT))

    while True:
        # ------------------ Get Distance ------------------
        buffer = bytearray(1024)
        length, client_addr = sock.recvfrom_into(buffer)
        data = buffer[:length]
        info = json.loads(data)
        distance = info["dist"]
        gz = info["gyro"]

        #distance = 500


        # Update LEDs
        leds_from_distance(distance)

        # ---------- Gyro ----------
        #gz = read_gyro_z()


        # ==================  Temp gz ===============
        #gz = 0
        print("Distance:", distance, "| Gyro Z:", gz)

        # ---------- Audio ----------
        now = time.monotonic()
        interval = interval_from_distance(distance) / 1000  # convert ms -> seconds
        update_audio(gz, distance)
        #if (now - last_beep_time) >= interval:
            #update_audio(gz, distance)
            #beep()
            #last_beep_time = now

        time.sleep(0.1)

finally:
     # Close socket if it exists
    try:
        sock.close()
    except NameError:
        print("Socket not created yet, skipping.")

    # Stop audio safely
    try:
        audio.stop()
    except NameError:
        print("Audio not initialized yet, skipping.")

    # Clear NeoPixels
    try:
        np.fill((0, 0, 0))
        np.show()
    except NameError:
        print("NeoPixels not initialized yet, skipping.")

    print("All systems shut down.")
