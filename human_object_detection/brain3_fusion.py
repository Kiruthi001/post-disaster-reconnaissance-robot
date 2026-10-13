from ultralytics import YOLO
import cv2

# Load models
person_model = YOLO("yolov8n.pt")
pose_model = YOLO("yolov8n-pose.pt")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # ---------------- BRAIN 1 ----------------
    person_results = person_model(frame, stream=True)
    brain1_human = False

    for r in person_results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = person_model.names[cls_id]

            if label == "person" and conf > 0.6:
                brain1_human = True

    # ---------------- BRAIN 2 ----------------
    pose_results = pose_model(frame, stream=True)
    brain2_human = False

    for r in pose_results:
        if r.keypoints is not None and len(r.keypoints.xy) > 0:
            brain2_human = True

    # ---------------- FINAL DECISION ----------------
    human_detected = brain1_human or brain2_human

    status = "HUMAN CONFIRMED" if human_detected else "NO HUMAN"
    color = (0, 255, 0) if human_detected else (0, 0, 255)

    cv2.putText(frame, status, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Rescue Robot - Human Detection System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
