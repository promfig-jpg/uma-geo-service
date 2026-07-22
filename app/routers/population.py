from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.population_service import find_population_dataset


router = APIRouter(
    prefix="/population",
    tags=["Population"]
)


@router.post("/dataset")
async def population_dataset(data: GeoRequest):
    try:
    dataset = await find_population_dataset(
    data.latitude,
    data.longitude,
    year=2025,
    iso3="BRA"
)

        return {
            "success": True,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "dataset": dataset,
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
