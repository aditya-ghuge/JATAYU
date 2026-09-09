"""Building camera configuration used to validate occupancy events.

This deliberately describes only stable building metadata. Video source details
remain in ``app/config.py`` so existing single-camera deployments keep working.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CameraDefinition:
    camera_id: str
    name: str
    role: str = "internal"


class BuildingConfig:
    def __init__(self, cameras: list[CameraDefinition]):
        self.cameras = {camera.camera_id: camera for camera in cameras}

    @classmethod
    def from_json(cls, config_path: str | Path) -> "BuildingConfig":
        with open(config_path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return cls([CameraDefinition(**camera) for camera in data["cameras"]])

    def has_camera(self, camera_id: str) -> bool:
        return camera_id in self.cameras
