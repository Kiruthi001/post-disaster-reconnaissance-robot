import cv2
from ultralytics import YOLO
import requests
import sys

# Load models
person_model = YOLO("yolov8n.pt")
pose_model = YOLO("yolov8n-pose.pt")

# Connect to /dev/video3 (Robot-AI)
cap = cv2.VideoCapture(3)
SERVER_URL = "http://127.0.0.1:5001/update_human"

print("AI Vision Active. Sending data to Dashboard...")

try:
    while True:
        ret, frame = cap.read()
        if not ret: break

        # Detection Logic
        res1 = person_model(frame, stream=True, verbose=False)
        brain1 = any(person_model.names[int(b.cls[0])] == "person" and float(b.conf[0]) > 0.6 
                     for r in res1 for b in r.boxes)

        res2 = pose_model(frame, stream=True, verbose=False)
        brain2 = any(r.keypoints is not None and len(r.keypoints.xy) > 0 for r in res2)

        human_detected = brain1 or brain2

        # Send to Flask Server
        try:
            requests.post(SERVER_URL, json={"human_found": human_detected}, timeout=0.05)
        except:
            pass # Server might be restarting

except KeyboardInterrupt:
    pass
finally:
    cap.release()
