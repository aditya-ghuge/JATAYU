from sqlalchemy import Column, Integer, String, Float
from database import Base

class BuildingZone(Base):
    __tablename__ = "building_zones"

    id = Column(Integer, primary_key=True, index=True)
    zone_name = Column(String, unique=True, nullable=False)

    smoke = Column(Float, default=0)
    temperature = Column(Float, default=25)
    gas = Column(Float, default=0)

    crowd_density = Column(Float, default=0)

    risk_level = Column(String, default="GREEN")
    sensor_status = Column(String, default="ACTIVE")