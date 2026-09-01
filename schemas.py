from pydantic import BaseModel

class ZoneUpdate(BaseModel):
    zone_name: str
    smoke: float
    temperature: float
    gas: float
    crowd_density: float