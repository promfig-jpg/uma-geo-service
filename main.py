from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import h3

app = FastAPI(
    title="UrbanMotoAds H3 API",
    description="API para converter coordenadas GPS em células H3.",
    version="1.0.0",
)


class H3Request(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    resolution: int = Field(default=9, ge=0, le=15)


@app.get("/")
def home():
    return {
        "success": True,
        "service": "UrbanMotoAds H3 API",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "success": True,
        "status": "healthy",
    }


@app.post("/h3")
def coordinates_to_h3(data: H3Request):
    try:
        h3_index = h3.latlng_to_cell(
            data.latitude,
            data.longitude,
            data.resolution,
        )

        center_latitude, center_longitude = h3.cell_to_latlng(h3_index)

        return {
            "success": True,
            "h3_index": h3_index,
            "resolution": data.resolution,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "cell_center": {
                "latitude": center_latitude,
                "longitude": center_longitude,
            },
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível calcular o índice H3: {str(error)}",
        )
