import cv2
from .base import BaseVideoSource


class FileVideoSource(BaseVideoSource):
    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath

    def start(self):
        self.cap = cv2.VideoCapture(self.filepath)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video file: {self.filepath}")
