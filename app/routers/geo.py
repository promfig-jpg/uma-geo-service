from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.h3_service import coordinates_to_h3
from app.services.geocoding_service import reverse_geocode


router = APIRouter(prefix="/geo", tags=["Geo"])


@router.post("/enrich")
async def enrich(data: GeoRequest):
    try:
        h3_data = coordinates_to_h3(
            data.latitude,
            data.longitude,
            data.resolution
        )

        geocoding_data = await reverse_geocode(
            data.latitude,
            data.longitude
        )

        return {
            "success": True,
            "latitude": data.latitude,
            "longitude": data.longitude,
            **h3_data,
            **geocoding_data
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
