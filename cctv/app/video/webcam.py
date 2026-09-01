import cv2
from .base import BaseVideoSource


class WebcamSource(BaseVideoSource):
    def __init__(self, device_id=0):
        super().__init__()
        try:
            self.device_id = int(device_id)
        except ValueError:
            self.device_id = 0

    def start(self):
        self.cap = cv2.VideoCapture(self.device_id)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam with device ID: {self.device_id}"
            )
