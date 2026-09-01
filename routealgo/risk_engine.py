"""
ResQRoute AI - Risk Engine Module
=================================
Calculates normalized individual sensor risk scores and transparently combines
them into a single 0-100 zone risk score. Maps scores to RiskState categories:
SAFE, MODERATE, HIGH, CRITICAL, and UNKNOWN.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from config import (
    SENSOR_WEIGHTS,
    SENSOR_RANGES,
    RiskState,
    RISK_THRESHOLDS,
    SensorHealth
)
from sensor_manager import SensorManager, SensorReading


@dataclass
class ZoneRiskReport:
    """Detailed risk assessment for a specific building zone."""
    zone_id: str
    risk_score: float
    risk_state: RiskState
    uncertainty_score: float
    is_critical: bool
    breakdown: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


def calculate_temperature_risk(temp_celsius: float) -> float:
    """
    Normalizes temperature reading (°C) into a 0.0 - 100.0 risk score.
    Piecewise linear interpolation based on fire safety danger thresholds.
    """
    cfg = SENSOR_RANGES["temperature"]
    min_safe = cfg["min_safe"]      # 20°C
    moderate = cfg["moderate"]      # 45°C
    high = cfg["high"]              # 60°C
    critical = cfg["critical"]      # 80°C

    if temp_celsius <= min_safe:
        return 0.0
    elif temp_celsius <= moderate:
        # 20°C to 45°C -> Risk 0 to 30
        return 0.0 + (temp_celsius - min_safe) / (moderate - min_safe) * 30.0
    elif temp_celsius <= high:
        # 45°C to 60°C -> Risk 30 to 70
        return 30.0 + (temp_celsius - moderate) / (high - moderate) * 40.0
    elif temp_celsius <= critical:
        # 60°C to 80°C -> Risk 70 to 100
        return 70.0 + (temp_celsius - high) / (critical - high) * 30.0
    else:
        return 100.0


def calculate_gas_risk(gas_ppm: float) -> float:
    """
    Normalizes gas/smoke concentration (ppm) into a 0.0 - 100.0 risk score.
    Reflects toxicity and visibility loss caused by combustion particulates.
    """
    cfg = SENSOR_RANGES["gas"]
    min_safe = cfg["min_safe"]      # 30 ppm
    moderate = cfg["moderate"]      # 100 ppm
    high = cfg["high"]              # 250 ppm
    critical = cfg["critical"]      # 400 ppm

    if gas_ppm <= min_safe:
        return 0.0
    elif gas_ppm <= moderate:
        # 30 to 100 ppm -> Risk 0 to 30
        return 0.0 + (gas_ppm - min_safe) / (moderate - min_safe) * 30.0
    elif gas_ppm <= high:
        # 100 to 250 ppm -> Risk 30 to 70
        return 30.0 + (gas_ppm - moderate) / (high - moderate) * 40.0
    elif gas_ppm <= critical:
        # 250 to 400 ppm -> Risk 70 to 100
        return 70.0 + (gas_ppm - high) / (critical - high) * 30.0
    else:
        return 100.0


def calculate_flame_risk(flame_value: float) -> float:
    """
    Normalizes flame sensor output into a 0.0 - 100.0 risk score.
    Handles both binary IR flame sensors (0 or 1) and analog optical index (0.0 to 1.0).
    """
    threshold = SENSOR_RANGES["flame"]["threshold"]
    if flame_value >= 1.0:
        return 100.0
    elif flame_value >= threshold:
        # Linear scaling above threshold
        return 70.0 + ((flame_value - threshold) / (1.0 - threshold)) * 30.0
    elif flame_value > 0.0:
        return (flame_value / threshold) * 40.0
    else:
        return 0.0


def get_risk_state_from_score(score: float, has_valid_sensors: bool = True) -> RiskState:
    """Classifies risk score into standardized categories."""
    if not has_valid_sensors:
        return RiskState.UNKNOWN

    if score <= RISK_THRESHOLDS["SAFE_MAX"]:
        return RiskState.SAFE
    elif score <= RISK_THRESHOLDS["MODERATE_MAX"]:
        return RiskState.MODERATE
    elif score <= RISK_THRESHOLDS["HIGH_MAX"]:
        return RiskState.HIGH
    else:
        return RiskState.CRITICAL


class RiskEngine:
    """
    Evaluates risk and hazard states for building zones using transparent multi-sensor fusion.
    """

    def __init__(self, sensor_weights: Optional[Dict[str, float]] = None):
        self.sensor_weights = sensor_weights or SENSOR_WEIGHTS

    def calculate_zone_risk(self, zone_id: str, sensor_manager: SensorManager) -> ZoneRiskReport:
        """
        Combines temperature, gas, and flame readings for a zone into an explainable risk score.
        Formula: risk = (temp_risk * W_temp) + (gas_risk * W_gas) + (flame_risk * W_flame)
        """
        readings = sensor_manager.get_all_zone_readings(zone_id)
        uncertainty = sensor_manager.calculate_zone_uncertainty(zone_id)

        # Check if we have any valid online/degraded sensor readings
        valid_readings = {
            st: r for st, r in readings.items()
            if r.status in [SensorHealth.ONLINE, SensorHealth.DEGRADED]
        }

        # Raw reading values (default to baseline safe if missing)
        temp_reading = readings.get("temperature")
        gas_reading = readings.get("gas")
        flame_reading = readings.get("flame")

        raw_temp = temp_reading.value if temp_reading else 20.0
        raw_gas = gas_reading.value if gas_reading else 30.0
        raw_flame = flame_reading.value if flame_reading else 0.0

        # Sub-risk scores (0 - 100)
        temp_risk = calculate_temperature_risk(raw_temp)
        gas_risk = calculate_gas_risk(raw_gas)
        flame_risk = calculate_flame_risk(raw_flame)

        # Weighted calculation
        w_temp = self.sensor_weights.get("temperature", 0.35)
        w_gas = self.sensor_weights.get("gas", 0.40)
        w_flame = self.sensor_weights.get("flame", 0.25)

        combined_risk = (temp_risk * w_temp) + (gas_risk * w_gas) + (flame_risk * w_flame)
        combined_risk = round(min(100.0, max(0.0, combined_risk)), 2)

        # Determine risk state
        has_valid_sensors = len(valid_readings) > 0
        risk_state = get_risk_state_from_score(combined_risk, has_valid_sensors=has_valid_sensors)

        is_critical = (combined_risk > RISK_THRESHOLDS["HIGH_MAX"]) or (flame_risk >= 90.0 and temp_risk >= 70.0)

        # Build natural language explanation
        explanation_parts = []
        if flame_risk > 50.0:
            explanation_parts.append(f"Flame detected ({flame_risk:.0f}% risk)")
        if gas_risk > 30.0:
            explanation_parts.append(f"High gas/smoke ({raw_gas:.0f} ppm -> {gas_risk:.0f}% risk)")
        if temp_risk > 30.0:
            explanation_parts.append(f"Elevated temperature ({raw_temp:.1f}°C -> {temp_risk:.0f}% risk)")
        if uncertainty > 50.0:
            explanation_parts.append(f"High sensor uncertainty ({uncertainty:.0f}%)")

        if not explanation_parts:
            explanation = "Normal environmental readings (Safe)"
        else:
            explanation = "; ".join(explanation_parts)

        breakdown = {
            "raw_inputs": {
                "temperature": raw_temp,
                "gas": raw_gas,
                "flame": raw_flame
            },
            "sub_risks": {
                "temperature_risk": round(temp_risk, 2),
                "gas_risk": round(gas_risk, 2),
                "flame_risk": round(flame_risk, 2)
            },
            "weights": {
                "temperature": w_temp,
                "gas": w_gas,
                "flame": w_flame
            },
            "sensor_statuses": {
                st: r.status.value for st, r in readings.items()
            }
        }

        return ZoneRiskReport(
            zone_id=zone_id,
            risk_score=combined_risk,
            risk_state=risk_state,
            uncertainty_score=uncertainty,
            is_critical=is_critical,
            breakdown=breakdown,
            explanation=explanation
        )
