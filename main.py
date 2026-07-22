from app.routers.geo import router as geo_router

from app.routers.geocoding import router as geocoding_router
from fastapi import FastAPI

from app.routers.health import router as health_router
from app.routers.h3 import router as h3_router


app = FastAPI(
    title="UMA Geo Service",
    description="Geographic intelligence service for UrbanMotoAds",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "success": True,
        "service": "UMA Geo Service",
        "status": "online",
    }


app.include_router(health_router)
app.include_router(h3_router)
app.include_router(geocoding_router)
app.include_router(geo_router)
