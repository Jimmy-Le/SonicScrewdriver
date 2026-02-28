from machine import Pin
import rp2
import network
import time
import math
import ujson
import usocket
import gc

gc.collect()
# This is code from AI, cause most sources are very confusing and I have no idea how to do this otherwise

## ----------- Transmitter -------------- ##

def transmitterCode():
  ap = network.WLAN(network.AP_IF)                  # Create AP Object (Broadcasts WI-FI), AP_IF makes it act as a WIFI hotspot
  ap.active(True)                                   # Turn Wi-Fi AP on
  ap.config(essid ="PicoAP", password="Pico123")    # Set up the wifi name and password
  print("AP Started:", ap.ipconfig())               # Print out info to see if it 
  
  while True:
    stations = ap.status('stations')                # Get a list of (MAC_bytes, rssi_int) tuples for connected clients
  
    if stations:
      for mac, rssi in stations:                    # Get RSSI
        print("Connected device MAC:", mac, "RSSI:", rssi)
    else:
      print("No Stations Connected")

    time.sleep(2)                                   # Replace this with a timer system

## ------------- Scanner ---------------- ##

def scannerCode():
  wlan = network.WLAN(network.STA_IF)               # Create Station Object (Like a phone scanning wi-fi)
  wlan.active(True)                                 # Turn WIFI Scanning on
  wlan.connect("PicoAP", "Pico123")                 # Connect to the WIFI
  
  # while not wlan.isconnected():       
  #   time.sleep(1)

  AP_IP = "192.168.4.1"                # AP's fixed IP address (always this when hosting)
  sock = usocket.socket()              # Create empty "mailbox" for UDP messages
  sock.connect((AP_IP, 12345))         # Point mailbox at AP's IP + port 12345
  
  print("Connected")
  
  
  while True:
    rssi = wlan.status('rssi')                       # Get RSSI
    print("RSSI:", rssi_to_distance(rssi))
    data = ujson.dumps({"rssi": rssi_to_distance(rssi)})  # Turn RSSI into text: '{"rssi":-55}'
    sock.send(data)                  # Mail the text to AP (fire and forget UDP)
    time.sleep(2)                                    # Replace this with a timer system



## ---------- Distance Formula ---------- ##
# The formula to convert dBm to Meters

def rssi_to_distance(rssi, P0=-50, n=2.5):
  if rssi == 0:
    return float('inf')

  return 10 ** ((P0 - rssi) / (10 * n))

## -------------------------------------- ##

scannerCode()








