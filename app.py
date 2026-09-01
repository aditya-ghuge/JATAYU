from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import engine, Base, SessionLocal
import models
from schemas import ZoneUpdate
from services.risk_engine import calculate_risk


# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(title="ResQRoute AI Backend")


# -------------------------
# Database session
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Home
# -------------------------
@app.get("/")
def home():
    return {
        "message": "ResQRoute AI Backend is Running",
        "project": "PS14 - ResQRoute AI",
        "status": "success"
    }


# -------------------------
# Update Zone
# -------------------------
@app.post("/update-zone")
def update_zone(
    data: ZoneUpdate,
    db: Session = Depends(get_db)
):

    zone = db.query(models.BuildingZone).filter(
        models.BuildingZone.zone_name == data.zone_name
    ).first()

    # Create zone if it does not exist
    if not zone:
        zone = models.BuildingZone(
            zone_name=data.zone_name
        )
        db.add(zone)

    # Update sensor values
    zone.smoke = data.smoke
    zone.temperature = data.temperature
    zone.gas = data.gas
    zone.crowd_density = data.crowd_density

    # Calculate risk
    zone.risk_level = calculate_risk(
        data.smoke,
        data.temperature,
        data.gas
    )

    # Save changes
    db.commit()
    db.refresh(zone)

    return {
        "message": "Zone updated successfully",
        "zone": zone.zone_name,
        "risk": zone.risk_level
    }


# -------------------------
# Get Hazards
# -------------------------
@app.get("/hazards")
def get_hazards(
    db: Session = Depends(get_db)
):

    zones = db.query(models.BuildingZone).all()

    return [
        {
            "zone": zone.zone_name,
            "smoke": zone.smoke,
            "temperature": zone.temperature,
            "gas": zone.gas,
            "crowd_density": zone.crowd_density,
            "risk": zone.risk_level,
            "sensor_status": zone.sensor_status
        }
        for zone in zones
    ]


# -------------------------
# Dynamic Route
# -------------------------
@app.get("/route")
def get_route(
    start: str = "Room A",
    db: Session = Depends(get_db)
):

    zones = db.query(models.BuildingZone).all()

    # RED and UNKNOWN zones are considered blocked
    blocked = {
        zone.zone_name
        for zone in zones
        if zone.risk_level in ["RED", "UNKNOWN"]
    }

    # Temporary prototype routing logic
    # Later this will be replaced by Vedant's
    # NetworkX / A* routing algorithm.
    if "Corridor A" in blocked:
        route = [
            "Room A",
            "Corridor B",
            "Exit A"
        ]
    else:
        route = [
            "Room A",
            "Corridor A",
            "Exit B"
        ]

    return {
        "start": start,
        "blocked_zones": list(blocked),
        "recommended_route": route,
        "status": "DYNAMIC_ROUTE"
    }


# -------------------------
# Sensor Status
# -------------------------
@app.post("/sensor-status")
def update_sensor_status(
    zone_name: str,
    sensor_status: str,
    db: Session = Depends(get_db)
):

    zone = db.query(models.BuildingZone).filter(
        models.BuildingZone.zone_name == zone_name
    ).first()

    # Zone does not exist
    if not zone:
        raise HTTPException(
            status_code=404,
            detail="Zone not found"
        )

    # Convert status to uppercase
    sensor_status = sensor_status.upper()

    # Validate sensor status
    if sensor_status not in ["ONLINE", "OFFLINE"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sensor status. Use ONLINE or OFFLINE."
        )

    zone.sensor_status = sensor_status

    # If sensor is offline, mark risk as UNKNOWN
    if sensor_status == "OFFLINE":
        zone.risk_level = "UNKNOWN"

    db.commit()
    db.refresh(zone)

    return {
        "zone": zone.zone_name,
        "sensor_status": zone.sensor_status,
        "risk": zone.risk_level
    }


# -------------------------
# Building Status
# -------------------------
@app.get("/building-status")
def building_status(
    db: Session = Depends(get_db)
):

    zones = db.query(models.BuildingZone).all()

    total = len(zones)

    green = sum(
        1 for zone in zones
        if zone.risk_level == "GREEN"
    )

    yellow = sum(
        1 for zone in zones
        if zone.risk_level == "YELLOW"
    )

    orange = sum(
        1 for zone in zones
        if zone.risk_level == "ORANGE"
    )

    red = sum(
        1 for zone in zones
        if zone.risk_level == "RED"
    )

    unknown = sum(
        1 for zone in zones
        if zone.risk_level == "UNKNOWN"
    )

    return {
        "total_zones": total,
        "safe": green,
        "moderate": yellow,
        "high": orange,
        "critical": red,
        "unknown": unknown
    }