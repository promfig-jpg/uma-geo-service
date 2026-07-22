from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.geocoding_service import reverse_geocode


router = APIRouter(prefix="/reverse", tags=["Geocoding"])


@router.post("")
async def reverse(data: GeoRequest):
    try:
        result = await reverse_geocode(
            data.latitude,
            data.longitude
        )

        return {
            "success": True,
            "latitude": data.latitude,
            "longitude": data.longitude,
            **result
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
