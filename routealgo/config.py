"""
ResQRoute AI - Configuration Module
====================================
Centralized configuration for sensor weights, risk thresholds,
cost calculation weights, sensor health states, and routing parameters.

All values are fully configurable to adapt to different facility safety standards.
"""

from enum import Enum


# ==========================================
# 1. SENSOR RISK CALCULATION WEIGHTS (Sum = 1.0)
# ==========================================
# Temperature: Indicates heat / fire intensity build-up
# Gas/Smoke: Indicates inhalation hazard or toxic smoke spread
# Flame: Direct optical/infrared confirmation of open fire
SENSOR_WEIGHTS = {
    "temperature": 0.35,
    "gas": 0.40,
    "flame": 0.25,
}

# ==========================================
# 2. SENSOR NORMALIZATION RANGES
# ==========================================
# Raw sensor readings are normalized to a 0.0 - 100.0 risk scale
# Sensor bounds: (min_safe, moderate, high, critical)
SENSOR_RANGES = {
    "temperature": {
        "min_safe": 20.0,    # deg C (Room temperature, 0% risk)
        "moderate": 45.0,    # deg C (Elevated heat)
        "high": 60.0,        # deg C (Dangerous heat)
        "critical": 80.0     # deg C (Direct fire heat, 100% risk)
    },
    "gas": {
        "min_safe": 30.0,    # ppm (Clean indoor air, 0% risk)
        "moderate": 100.0,   # ppm (Moderate smoke/gas)
        "high": 250.0,       # ppm (Hazardous smoke)
        "critical": 400.0    # ppm (Lethal/dense smoke, 100% risk)
    },
    "flame": {
        # Flame sensors typically output binary (0/1) or analog detection index (0.0 to 1.0)
        "threshold": 0.5,    # Value >= 0.5 triggers flame danger (100% risk)
    }
}

# ==========================================
# 3. RISK STATES & THRESHOLDS (0 - 100 Scale)
# ==========================================
class RiskState(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


RISK_THRESHOLDS = {
    "SAFE_MAX": 20.0,         # 0  - 20
    "MODERATE_MAX": 40.0,     # 21 - 40
    "HIGH_MAX": 70.0,         # 41 - 70
    "CRITICAL_MIN": 70.01     # 71 - 100
}

# ==========================================
# 4. SENSOR HEALTH & UNCERTAINTY
# ==========================================
class SensorHealth(str, Enum):
    ONLINE = "ONLINE"        # Sensor operating normally
    DEGRADED = "DEGRADED"    # Erratic or noisy readings
    STALE = "STALE"          # No heartbeat for > timeout
    OFFLINE = "OFFLINE"      # Zero communication / disconnected


# Uncertainty penalty score added to zone based on sensor health (0 - 100 scale)
UNCERTAINTY_SCORES = {
    SensorHealth.ONLINE: 0.0,
    SensorHealth.DEGRADED: 35.0,
    SensorHealth.STALE: 55.0,
    SensorHealth.OFFLINE: 85.0
}

SENSOR_TIMEOUT_SECONDS = 15.0  # Time before an unrefreshed sensor is marked STALE

# ==========================================
# 5. DYNAMIC EDGE COST WEIGHTS
# ==========================================
# total_cost = distance * W_DISTANCE + risk * W_RISK + crowd * W_CROWD + uncertainty * W_UNCERTAINTY
COST_WEIGHTS = {
    "W_DISTANCE": 1.0,        # Standard physical distance factor
    "W_RISK": 2.5,            # Multiplier for zone risk score (0-100)
    "W_CROWD": 0.4,           # Multiplier for crowd congestion count/density (0-100)
    "W_UNCERTAINTY": 1.5      # Multiplier for sensor uncertainty penalty (0-100)
}

# Penalty applied to forbid traversal through CRITICAL zones or blocked exits
IMPASSABLE_COST_PENALTY = 1_000_000.0  # Effectively infinity in Dijkstra

# Minimum delta cost reduction required to trigger dynamic rerouting notification
REROUTE_THRESHOLD_DELTA = 15.0
