from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.h3_service import coordinates_to_h3


router = APIRouter(prefix="/h3", tags=["H3"])


@router.post("")
def get_h3(data: GeoRequest):
    try:
        result = coordinates_to_h3(
            data.latitude,
            data.longitude,
            data.resolution
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
