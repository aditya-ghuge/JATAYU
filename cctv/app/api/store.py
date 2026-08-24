import threading
from typing import Dict, List, Any


class StateStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_state: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.latest_frame: bytes = None

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


# Global Singleton
store = StateStore()
