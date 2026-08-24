from typing import List, Dict
from detection.models import Detection
from .models import TrackedPerson


class PersonTracker:
    def __init__(self, history_length: int = 30, max_age: int = 30):
        """
        Initializes the Person Tracker.
        Args:
            history_length: Maximum number of previous positions to store per person.
            max_age: Maximum number of frames to keep a track alive after losing it.
        """
        self.tracks: Dict[int, TrackedPerson] = {}
        self.history_length = history_length
        self.max_age = max_age

    def update(self, detections: List[Detection]) -> List[TrackedPerson]:
        """
        Updates the tracker with new detections and returns the currently tracked people.
        """
        current_track_ids = set()

        for det in detections:
            if det.track_id is None:
                continue

            track_id = det.track_id
            current_track_ids.add(track_id)

            # Calculate center of bounding box
            x1, y1, x2, y2 = det.bbox
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            center = (center_x, center_y)

            if track_id in self.tracks:
                # Update existing track
                person = self.tracks[track_id]
                person.bbox = det.bbox
                person.confidence = det.confidence
                person.time_since_update = 0
                person.history.append(center)

                # Keep history within limit
                if len(person.history) > self.history_length:
                    person.history.pop(0)
            else:
                # Create new track
                self.tracks[track_id] = TrackedPerson(
                    track_id=track_id,
                    bbox=det.bbox,
                    history=[center],
                    confidence=det.confidence,
                    time_since_update=0,
                )

        # Increase time_since_update for lost tracks, and remove if they exceed max_age
        lost_tracks = set(self.tracks.keys()) - current_track_ids
        for track_id in lost_tracks:
            self.tracks[track_id].time_since_update += 1
            if self.tracks[track_id].time_since_update > self.max_age:
                del self.tracks[track_id]

        # Only return tracks that are currently visible (or very recently lost)
        # to prevent drawing bounding boxes for people who aren't there
        active_tracks = [p for p in self.tracks.values() if p.time_since_update == 0]
        return active_tracks
