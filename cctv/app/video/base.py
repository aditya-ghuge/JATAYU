import time
from abc import ABC, abstractmethod


class BaseVideoSource(ABC):
    def __init__(self):
        self.cap = None
        self.fps = 0
        self._prev_time = 0

    @abstractmethod
    def start(self):
        """Initialize the video capture."""
        pass

    def read(self):
        """Read a frame and calculate FPS."""
        if not self.cap:
            return False, None

        ret, frame = self.cap.read()

        # Calculate FPS
        current_time = time.time()
        time_diff = current_time - self._prev_time
        if time_diff > 0:
            self.fps = 1.0 / time_diff
        self._prev_time = current_time

        return ret, frame

    def release(self):
        """Release the video capture."""
        if self.cap:
            self.cap.release()

    def get_fps(self):
        """Return the current FPS."""
        return self.fps
