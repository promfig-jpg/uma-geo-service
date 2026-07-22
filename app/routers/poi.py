from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.poi_service import get_nearby_pois


router = APIRouter(prefix="/pois", tags=["POIs"])


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
