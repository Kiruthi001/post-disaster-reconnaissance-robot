import socket
import pynmea2
import threading
from flask import Flask, jsonify, request
import time
import json
import serial

app = Flask(__name__)

# Core Data Structure
latest_data = {
    "lat": 0.0,
    "lon": 0.0,
    "human_found": False,   # AI Status (Replaced Accelerometer)
    "ultra_state": "WAITING",
    "hlk": {
        "status": "No Target",
        "mov_dist": 0,
        "mov_energy": 0,
        "sta_dist": 0,
        "sta_energy": 0,
        "detect_dist": 0
    }
}

# --- ENDPOINTS ---

@app.route('/update_human', methods=['POST'])
def update_human():
    """Receives detection status from the local YOLO script."""
    global latest_data
    try:
        data = request.json
        latest_data["human_found"] = data.get("human_found", False)
        return "OK", 200
    except Exception as e:
        return str(e), 400

@app.route('/gps')
def get_dashboard_data():
    """Main endpoint for the Dashboard to poll all sensor data."""
    response = jsonify(latest_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# --- WORKER THREADS ---

def ultra_worker():
    """Listens for Ultrasonic data from intel2.py bridge."""
    global latest_data
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("127.0.0.1", 5005))
    print("Ultrasonic Listener started on port 5005...")
    while True:
        try:
            data, addr = udp_sock.recvfrom(1024)
            latest_data["ultra_state"] = data.decode().strip()
        except Exception as e:
            print(f"Ultra receiver error: {e}")

def gps_worker():
    """Connects to phone GPS stream."""
    global latest_data
    PHONE_IP = "10.41.141.142"
    PHONE_PORT = 5000
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((PHONE_IP, PHONE_PORT))
            buffer = ""
            while True:
                data = sock.recv(1024).decode('utf-8', errors='ignore')
                if not data: break
                buffer += data
                lines = buffer.split("\n")
                buffer = lines.pop()
                for line in lines:
                    if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
                        msg = pynmea2.parse(line)
                        if msg.latitude != 0:
                            latest_data["lat"] = msg.latitude
                            latest_data["lon"] = msg.longitude
        except:
            time.sleep(2)

def radar_worker():
    """Reads HLK-LD2410C Radar data via Serial."""
    global latest_data
    while True:
        try:
            ser_radar = serial.Serial('/dev/ttyAMA0', 256000, timeout=1)
            while True:
                header = ser_radar.read(4)
                if header == b'\xf4\xf3\xf2\xf1':
                    packet = ser_radar.read(19)
                    if len(packet) == 19 and packet[-4:] == b'\xf8\xf7\xf6\xf5':
                        status = packet[4]
                        status_map = {0: "No Target", 1: "Moving", 2: "Static", 3: "Both"}
                        latest_data["hlk"] = {
                            "status": status_map.get(status, '??'),
                            "mov_dist": int.from_bytes(packet[5:7], byteorder='little'),
                            "mov_energy": packet[7],
                            "sta_dist": int.from_bytes(packet[8:10], byteorder='little'),
                            "sta_energy": packet[10],
                            "detect_dist": int.from_bytes(packet[11:13], byteorder='little')
                        }
        except:
            time.sleep(2)
        finally:
            if 'ser_radar' in locals(): ser_radar.close()

if __name__ == '__main__':
    # Initialize background processes
    threading.Thread(target=ultra_worker, daemon=True).start()
    threading.Thread(target=gps_worker, daemon=True).start()
    threading.Thread(target=radar_worker, daemon=True).start()
    
    print("RescueBot Server starting on port 5001...")
    app.run(host='0.0.0.0', port=5001)
