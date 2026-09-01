import cv2
from .base import BaseVideoSource


class RTSPVideoSource(BaseVideoSource):
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.rtsp_url = rtsp_url

    def start(self):
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open RTSP stream: {self.rtsp_url}")
