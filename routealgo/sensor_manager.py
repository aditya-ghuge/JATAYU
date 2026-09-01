"""
ResQRoute AI - Sensor Manager Module
====================================
Manages sensor inputs, health states (ONLINE, DEGRADED, STALE, OFFLINE),
timeouts, uncertainty scoring, and supports easy plug-and-play extension
for new sensor types (e.g. CO2, Thermal Imagers, Structural Acoustic Sensors).
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from config import (
    SensorHealth,
    UNCERTAINTY_SCORES,
    SENSOR_TIMEOUT_SECONDS,
    SENSOR_WEIGHTS
)


@dataclass
class SensorReading:
    """Represents a single reading from a physical or simulated sensor."""
    sensor_type: str
    value: float
    status: SensorHealth = SensorHealth.ONLINE
    timestamp: float = field(default_factory=time.time)
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_stale(self, current_time: Optional[float] = None, timeout: float = SENSOR_TIMEOUT_SECONDS) -> bool:
        """Check if the sensor reading has expired due to missing heartbeat."""
        now = current_time if current_time is not None else time.time()
        return (now - self.timestamp) > timeout


class SensorManager:
    """
    Central repository for zone sensor readings and sensor health management.
    Designed for easy integration with ESP32 microcontrollers and IoT MQTT/HTTP brokers.
    """

    def __init__(self):
        # Nested dictionary: zone_id -> {sensor_type -> SensorReading}
        self.zone_readings: Dict[str, Dict[str, SensorReading]] = {}
        # Registered sensor types (allows easy expansion)
        self.registered_sensors: set = set(SENSOR_WEIGHTS.keys())

    def register_sensor_type(self, sensor_type: str, default_unit: str = ""):
        """Register a new physical or virtual sensor type."""
        self.registered_sensors.add(sensor_type)

    def update_sensor_data(
        self,
        zone_id: str,
        sensor_type: str,
        value: float,
        status: SensorHealth = SensorHealth.ONLINE,
        timestamp: Optional[float] = None,
        unit: str = ""
    ) -> SensorReading:
        """
        Record or update a sensor reading for a specific zone.
        Called by FastAPI endpoints when ESP32 or simulated hardware pushes data.
        """
        if zone_id not in self.zone_readings:
            self.zone_readings[zone_id] = {}

        t = timestamp if timestamp is not None else time.time()
        reading = SensorReading(
            sensor_type=sensor_type,
            value=float(value),
            status=status,
            timestamp=t,
            unit=unit
        )
        self.zone_readings[zone_id][sensor_type] = reading
        return reading

    def update_bulk_telemetry(self, zone_id: str, telemetry: Dict[str, Any], timestamp: Optional[float] = None):
        """
        Convenience method to ingest a multi-sensor payload from an ESP32 node.
        Example telemetry: {"temperature": 28.5, "gas": 42.0, "flame": 0.0, "status": "ONLINE"}
        """
        status_str = telemetry.get("status", "ONLINE")
        try:
            health_status = SensorHealth(status_str)
        except ValueError:
            health_status = SensorHealth.ONLINE

        t = timestamp if timestamp is not None else time.time()

        for sensor_type in ["temperature", "gas", "flame"]:
            if sensor_type in telemetry:
                val = telemetry[sensor_type]
                self.update_sensor_data(
                    zone_id=zone_id,
                    sensor_type=sensor_type,
                    value=val,
                    status=health_status,
                    timestamp=t
                )

    def get_sensor_reading(self, zone_id: str, sensor_type: str) -> Optional[SensorReading]:
        """Retrieve the latest reading for a specific sensor in a zone."""
        zone = self.zone_readings.get(zone_id, {})
        reading = zone.get(sensor_type)
        if reading is not None and reading.status == SensorHealth.ONLINE:
            # Check for stale heartbeat
            if reading.is_stale():
                reading.status = SensorHealth.STALE
        return reading

    def get_all_zone_readings(self, zone_id: str) -> Dict[str, SensorReading]:
        """Retrieve all active sensor readings for a zone."""
        readings = self.zone_readings.get(zone_id, {})
        # Update STALE status on the fly if needed
        for r in readings.values():
            if r.status == SensorHealth.ONLINE and r.is_stale():
                r.status = SensorHealth.STALE
        return readings

    def calculate_zone_uncertainty(self, zone_id: str) -> float:
        """
        Calculates sensor uncertainty penalty score (0.0 to 100.0) for a zone.
        If sensors are missing, degraded, stale, or offline, uncertainty increases.
        """
        readings = self.get_all_zone_readings(zone_id)
        if not readings:
            # No sensors at all -> High uncertainty
            return UNCERTAINTY_SCORES[SensorHealth.OFFLINE]

        uncertainty_sum = 0.0
        expected_sensor_count = len(self.registered_sensors)

        for sensor_type in self.registered_sensors:
            reading = readings.get(sensor_type)
            if reading is None:
                # Missing sensor treated as OFFLINE uncertainty
                uncertainty_sum += UNCERTAINTY_SCORES[SensorHealth.OFFLINE]
            else:
                uncertainty_sum += UNCERTAINTY_SCORES.get(reading.status, UNCERTAINTY_SCORES[SensorHealth.OFFLINE])

        avg_uncertainty = uncertainty_sum / max(1, expected_sensor_count)
        return min(100.0, max(0.0, avg_uncertainty))

    def reset_zone(self, zone_id: str):
        """Clear sensor readings for a zone (used during testing)."""
        if zone_id in self.zone_readings:
            del self.zone_readings[zone_id]

    def reset_all(self):
        """Clear all sensor readings across the building."""
        self.zone_readings.clear()
