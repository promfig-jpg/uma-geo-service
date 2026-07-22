from pydantic import BaseModel, Field


class GeoRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    resolution: int = Field(default=9, ge=0, le=15)
