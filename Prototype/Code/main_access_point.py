import machine
import time
import network

led = machine.Pin("LED", machine.Pin.OUT)
led.value(0)

ssid = "Chimaera_Pico"
password = "Friend_Hotspot"

ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)

while not ap.active():
    time.sleep(0.1)

print("Access point active")
print("IP config:", ap.ifconfig())

try:
    while True:
        led.toggle()
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    print("Turning AP off")
    ap.active(False)
    led.value(0)