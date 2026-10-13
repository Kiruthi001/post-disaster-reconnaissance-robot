from ultralytics import YOLO
import cv2

# Load YOLOv8 Pose model
model = YOLO("yolov8n-pose.pt")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, stream=True)

    human_present = False

    for r in results:
        if r.keypoints is not None:
            keypoints = r.keypoints.xy
            if keypoints is not None and len(keypoints) > 0:
                human_present = True

    # STATUS DISPLAY
    status = "HUMAN (POSE PART DETECTED)" if human_present else "NO HUMAN"
    color = (0, 255, 0) if human_present else (0, 0, 255)

    cv2.putText(frame, status, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Brain 2 - Pose Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
