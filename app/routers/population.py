from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.population_service import (
    find_population_dataset,
    get_population_estimate,
)


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


@router.post("/estimate")
async def population_estimate(data: GeoRequest):
    try:
        result = await get_population_estimate(
            data.latitude,
            data.longitude,
            year=2025,
            iso3="BRA"
        )

        return {
            "latitude": data.latitude,
            "longitude": data.longitude,
            **result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
