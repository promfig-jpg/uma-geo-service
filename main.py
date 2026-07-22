from fastapi import FastAPI

from app.routers.health import router as health_router


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
