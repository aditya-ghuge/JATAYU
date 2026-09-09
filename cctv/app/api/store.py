import threading
from typing import Callable, Dict, List, Any


class StateStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_state: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.latest_frame: bytes = None
        self._emergency_start_handler: Callable[[], Dict[str, Any]] | None = None

    def update_state(self, state: Dict[str, Any]):
        with self.lock:
            self.latest_state = state

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            return self.latest_state.copy()

    def add_event(self, event: Dict[str, Any]):
        with self.lock:
            self.events.append(event)
            # Keep only last 100 events to prevent memory leak
            if len(self.events) > 100:
                self.events.pop(0)

    def get_events(self) -> List[Dict[str, Any]]:
        with self.lock:
            return self.events.copy()

    def update_frame(self, frame_bytes: bytes):
        with self.lock:
            self.latest_frame = frame_bytes

    def get_frame(self) -> bytes:
        with self.lock:
            return self.latest_frame

    def set_emergency_start_handler(self, handler: Callable[[], Dict[str, Any]]):
        """Register the live occupancy engine after the video pipeline starts."""
        with self.lock:
            self._emergency_start_handler = handler

    def start_emergency(self) -> Dict[str, Any]:
        with self.lock:
            handler = self._emergency_start_handler
        if handler is None:
            raise RuntimeError("Occupancy engine is not running")
        return handler()


# Global Singleton
store = StateStore()
