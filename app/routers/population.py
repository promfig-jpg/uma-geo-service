from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.models.population import PopulationBatchRequest

from app.services.population_service import (
    find_population_dataset,
)

from app.services.population_batch_service import (
    process_population_points,
)


router = APIRouter(
    prefix="/population",
    tags=["Population"],
)


@router.post("/dataset")
async def population_dataset(
    data: GeoRequest
):
    try:
        dataset = await find_population_dataset(
            data.latitude,
            data.longitude,
            year=2025,
            iso3="BRA",
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
            detail=str(error),
        )


@router.post("/batch")
async def population_batch(
    data: PopulationBatchRequest
):
    try:
        points = [
            point.model_dump()
            for point in data.points
        ]

        result = await process_population_points(
            points=points,
            iso3=data.iso3,
            year=data.year,
        )

        return result

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
