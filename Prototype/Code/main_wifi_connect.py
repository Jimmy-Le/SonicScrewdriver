import machine
import time
import network

led = machine.Pin("LED", machine.Pin.OUT)
led.value(0)

ssid = "Chimaera Cast"
password = "seanisnotjoe"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting...")
while not wlan.isconnected():
  time.sleep(1)

print("Connected to WiFi")
print("IP config:", wlan.ifconfig())

try:
    while True:
        led.toggle()
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    print("Turning AP off")
    wlan.active(False)
    led.value(0)