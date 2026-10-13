import board
import busio
import digitalio
import adafruit_rfm9x
import time
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SERVER_URL = "http://127.0.0.1:5001/gps"  # URL of your server.py endpoint
SEND_INTERVAL = 5                         # Seconds between LoRa transmissions
IST_OFFSET = timedelta(hours=5, minutes=30)

# --- LORA HARDWARE SETUP (From your Lucky Charm) ---
CS = digitalio.DigitalInOut(board.D27)
CS.direction = digitalio.Direction.OUTPUT
CS.value = True

RESET = digitalio.DigitalInOut(board.D17)
RESET.direction = digitalio.Direction.OUTPUT
RESET.value = True

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

print("Resetting LoRa chip...")
RESET.value = False
time.sleep(0.1)
RESET.value = True
time.sleep(0.1)

# Initialize the radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)
rfm9x.tx_power = 13
rfm9x.sync_word = 0x12

print(f"LoRa Bridge Started! Fetching from {SERVER_URL}")

# --- TRANSMISSION LOGIC ---
counter = 1

while True:
    try:
        # 1. Fetch data from the server.py API
        response = requests.get(SERVER_URL, timeout=2)
        if response.status_code == 200:
            data = response.json()
            
            # 2. Extract specific fields
            lat = data.get("lat", 0.0)
            lon = data.get("lon", 0.0)
            human = "YES" if data.get("human_found") else "NO"
            ultra = data.get("ultra_state", "N/A")
            
            # Radar Info (HLK)
            radar = data.get("hlk", {})
            r_status = radar.get("status", "No Target")
            r_dist = radar.get("detect_dist", 0)

            # 3. Create Timestamp (IST)
            ist_time = datetime.now() + IST_OFFSET
            formatted_time = ist_time.strftime("%H:%M:%S")

            # 4. Format the LoRa Message (Kept concise for LoRa packet limits)
            # Format: #Count [Time] GPS: Lat,Lon | Human: Y/N | Ultra: Status | Radar: Status(Dist)
            lora_msg = (
                f"#{counter} [{formatted_time}] "
                f"GPS:{lat:.4f},{lon:.4f} "
                f"HUMAN:{human} "
                f"ULTRA:{ultra} "
                f"RADAR:{r_status}({r_dist}cm)"
            )

            # 5. Transmit
            rfm9x.send(bytes(lora_msg, "utf-8"))
            print(f"Sent: {lora_msg}")
            
            counter += 1
        else:
            print(f"Server Error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("Waiting for server.py to start...")
    except Exception as e:
        print(f"Bridge Error: {e}")

    time.sleep(SEND_INTERVAL)