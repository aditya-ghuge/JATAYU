import cv2
import numpy as np
from ultralytics import YOLO
from typing import List
from .models import Detection


class YOLODetector:
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5):
        """
        Initialize the YOLO detector.
        Args:
            model_path: Path to the YOLO model file (e.g., yolov8n.pt). It will be downloaded if it doesn't exist.
            conf_threshold: Minimum confidence threshold for a detection to be considered valid.
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def predict(self, frame: np.ndarray) -> List[Detection]:
        """
        Run inference and tracking on a single frame and return a list of person detections.
        """
        # Run inference with tracking (persist=True keeps history between frames)
        # We use bytetrack.yaml as it generally handles brief occlusions better than the default botsort
        results = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", verbose=False
        )

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get the class ID
                class_id = int(box.cls[0].item())
                # Get the confidence score
                conf = box.conf[0].item()

                # Class 0 is "person", 67 is "cell phone" (FIRE), 41 is "cup" (SMOKE)
                if class_id in [0, 67, 41] and conf >= self.conf_threshold:
                    class_map = {0: "person", 67: "FIRE", 41: "SMOKE"}
                    class_name = class_map[class_id]

                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    # Extract track ID if available
                    track_id = int(box.id[0].item()) if box.id is not None else None

                    detections.append(
                        Detection(
                            class_id=class_id,
                            class_name=class_name,
                            confidence=conf,
                            bbox=(x1, y1, x2, y2),
                            track_id=track_id,
                        )
                    )

        return detections
