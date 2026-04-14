from machine import Pin
import usocket
import ujson
import rp2
import network
import time
import math
import gc

gc.collect()


# This is code from AI, cause most sources are very confusing and I have no idea how to do this otherwise

## ----------- Transmitter -------------- ##
ap = network.WLAN(network.AP_IF)                  # Create AP Object (Broadcasts WI-FI), AP_IF makes it act as a WIFI hotspot

def transmitterCode():
  ap = network.WLAN(network.AP_IF)                  # Create AP Object (Broadcasts WI-FI), AP_IF makes it act as a WIFI hotspot
  ap.active(True)                                   # Turn Wi-Fi AP on
  ap.config(essid ="PicoAP", password="12345678")    # Set up the wifi name and password
  
  while True:
    stations = ap.status('stations')                # Get a list of (MAC_bytes, rssi_int) tuples for connected clients
  
    if stations:
      for mac in stations:                          # Get RSSI
        print("Connected device MAC:", mac)
    else:
      print("No Stations Connected")

    time.sleep(2)                                   # Replace this with a timer system


## ---------- Distance Formula ---------- ##
# The formula to convert dBm to Meters

def rssi_to_distance(rssi, P0=-50, n=2.5):
  if rssi == 0:
    return float('inf')

  return 10 ** ((P0 - rssi) / (10 * n))

## -------------------------------------- ##


def cleanup_ap():
    try:
        sock.close()         # Close UDP listener
    except:
        pass
    ap.disconnect()          # Kick any clients
    ap.active(False)         # Turn hotspot off
    ap.deinit()              # Power down Wi-Fi chip
    print("AP cleaned up")




try:
  transmitterCode()
finally:
  cleanup_ap()








