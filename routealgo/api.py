"""
ResQRoute AI - REST API Engine (FastAPI)
========================================
Production-ready REST API for:
1. Ingesting real-time telemetry from ESP32 microcontrollers (Temperature, Gas, Flame).
2. Receiving real-time crowd metrics from CCTV / OpenCV computer vision nodes.
3. Managing emergency exit availability (access control / fire barrier integrations).
4. Providing real-time safe route guidance and explainability to emergency dashboards & mobile apps.
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from config import SensorHealth, RiskState
from building import BuildingGraph, create_sample_building
from sensor_manager import SensorManager
from risk_engine import RiskEngine
from routing import RoutingEngine, RouteResult


# Initialize FastAPI App
app = FastAPI(
    title="ResQRoute AI - Safe Evacuation Routing Engine",
    description="Explainable, dynamic risk-aware pathfinding API for emergency evacuation.",
    version="1.0.0"
)

# Global in-memory state
building: BuildingGraph = create_sample_building()
sensor_manager: SensorManager = SensorManager()
risk_engine: RiskEngine = RiskEngine()
routing_engine: RoutingEngine = RoutingEngine(risk_engine=risk_engine)


# ==========================================
# Pydantic Request/Response Models
# ==========================================
class TelemetryPayload(BaseModel):
    zone_id: str = Field(..., description="Target building zone (e.g. 'C1', 'R1')")
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    gas: Optional[float] = Field(None, description="Smoke/gas in ppm")
    flame: Optional[float] = Field(None, description="Flame detection index (0.0 to 1.0 or binary 0/1)")
    status: SensorHealth = Field(SensorHealth.ONLINE, description="Sensor operational status")


class CrowdPayload(BaseModel):
    zone_id: str = Field(..., description="Target building zone (e.g. 'C1')")
    crowd_count: float = Field(..., ge=0.0, description="Estimated crowd density / count (0-100)")


class ExitStatusPayload(BaseModel):
    exit_id: str = Field(..., description="Exit node identifier (e.g. 'EXIT1')")
    is_available: bool = Field(..., description="True if passable, False if locked/blocked")


class RouteQueryPayload(BaseModel):
    start_zone: str = Field(..., description="Starting room or corridor (e.g. 'R1')")


# ==========================================
# API Endpoints
# ==========================================
@app.get("/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "system": "ResQRoute AI",
        "zones_count": len(building.nodes),
        "available_exits": building.get_available_exits()
    }


@app.get("/building", tags=["Topology & State"])
def get_building_state():
    """Returns complete building topology, current node risks, crowd levels, and exit statuses."""
    zones_summary = {}
    for zone_id, node in building.nodes.items():
        risk_rep = risk_engine.calculate_zone_risk(zone_id, sensor_manager)
        zones_summary[zone_id] = {
            "name": node.name,
            "type": node.zone_type,
            "is_exit": node.is_exit,
            "is_available": node.is_available,
            "crowd_count": node.crowd_count,
            "risk_score": risk_rep.risk_score,
            "risk_state": risk_rep.risk_state.value,
            "uncertainty": risk_rep.uncertainty_score,
            "explanation": risk_rep.explanation
        }

    return {
        "name": building.name,
        "zones": zones_summary,
        "edges": [
            {
                "from": e.source,
                "to": e.target,
                "distance_m": e.distance,
                "is_blocked": e.is_blocked
            }
            for e in building.edges
        ]
    }


@app.post("/telemetry", tags=["Hardware / ESP32 Ingestion"])
def ingest_telemetry(payload: TelemetryPayload):
    """
    Ingest multi-sensor telemetry packet from an ESP32 hardware node.
    Updates the temperature, gas, and flame readings for the zone.
    """
    if payload.zone_id not in building.nodes:
        raise HTTPException(status_code=404, detail=f"Zone '{payload.zone_id}' not found in building graph.")

    if payload.temperature is not None:
        sensor_manager.update_sensor_data(
            zone_id=payload.zone_id,
            sensor_type="temperature",
            value=payload.temperature,
            status=payload.status,
            unit="°C"
        )
    if payload.gas is not None:
        sensor_manager.update_sensor_data(
            zone_id=payload.zone_id,
            sensor_type="gas",
            value=payload.gas,
            status=payload.status,
            unit="ppm"
        )
    if payload.flame is not None:
        sensor_manager.update_sensor_data(
            zone_id=payload.zone_id,
            sensor_type="flame",
            value=payload.flame,
            status=payload.status,
            unit="index"
        )

    # Calculate updated zone risk
    risk_rep = risk_engine.calculate_zone_risk(payload.zone_id, sensor_manager)

    return {
        "status": "success",
        "zone_id": payload.zone_id,
        "new_risk_score": risk_rep.risk_score,
        "risk_state": risk_rep.risk_state.value,
        "uncertainty": risk_rep.uncertainty_score,
        "explanation": risk_rep.explanation
    }


@app.post("/crowd", tags=["CCTV / Computer Vision Ingestion"])
def ingest_crowd(payload: CrowdPayload):
    """Ingest crowd congestion levels from CCTV / OpenCV human detection."""
    if payload.zone_id not in building.nodes:
        raise HTTPException(status_code=404, detail=f"Zone '{payload.zone_id}' not found.")

    building.update_crowd_data(payload.zone_id, payload.crowd_count)
    return {
        "status": "success",
        "zone_id": payload.zone_id,
        "crowd_count": payload.crowd_count
    }


@app.post("/exit-status", tags=["Access Control"])
def update_exit_door(payload: ExitStatusPayload):
    """Toggle availability of an emergency exit."""
    if payload.exit_id not in building.nodes or not building.nodes[payload.exit_id].is_exit:
        raise HTTPException(status_code=404, detail=f"Exit '{payload.exit_id}' not found.")

    building.update_exit_status(payload.exit_id, payload.is_available)
    return {
        "status": "success",
        "exit_id": payload.exit_id,
        "is_available": payload.is_available
    }


@app.get("/route", tags=["Routing Engine"])
def get_safest_route(start: str = Query("R1", description="Starting zone ID")):
    """
    Calculate the dynamic safest evacuation path from a starting location.
    Returns the optimal route, selected exit, cost, risk level, and full explanation.
    """
    if start not in building.nodes:
        raise HTTPException(status_code=404, detail=f"Starting zone '{start}' not found.")

    result: RouteResult = routing_engine.find_safest_route(
        building=building,
        start_zone=start,
        sensor_manager=sensor_manager
    )

    return result.to_dict()


@app.post("/reset", tags=["System"])
def reset_system():
    """Reset all sensors and crowd data back to baseline normal safe state."""
    sensor_manager.reset_all()
    for node in building.nodes.values():
        node.crowd_count = 0.0
        node.is_available = True
    return {"status": "success", "message": "System state reset to baseline safe conditions."}
