from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.geo import GeoRequest
from app.services.poi_service import (
    get_nearby_pois,
    get_h3_pois,
)


router = APIRouter(
    prefix="/pois",
    tags=["POIs"]
)


class H3PoiRequest(BaseModel):
    h3_index: str


@router.post("")
async def pois(data: GeoRequest):
    try:
        result = await get_nearby_pois(
            data.latitude,
            data.longitude
        )

        return {
            "latitude": data.latitude,
            "longitude": data.longitude,
            **result
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.post("/h3")
async def pois_by_h3(
    data: H3PoiRequest
):
    try:
        result = await get_h3_pois(
            data.h3_index
        )

        return result

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
