from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.h3_service import coordinates_to_h3
from app.services.geocoding_service import reverse_geocode
from app.services.street_service import calculate_street_importance
from app.cache.memory_cache import get_cache, set_cache


router = APIRouter(prefix="/geo", tags=["Geo"])


@router.post("/enrich")
async def enrich(data: GeoRequest):
    try:
        h3_data = coordinates_to_h3(
            data.latitude,
            data.longitude,
            data.resolution
        )

        h3_index = h3_data["h3_index"]

        cached_data = get_cache(h3_index)

        if cached_data:
            return {
                "success": True,
                "latitude": data.latitude,
                "longitude": data.longitude,
                **h3_data,
                **cached_data,
                "cache": {
                    "hit": True
                }
            }

        geocoding_data = await reverse_geocode(
            data.latitude,
            data.longitude
        )

        highway_type = geocoding_data.get(
            "street_type"
        )

        street_importance = calculate_street_importance(
            highway_type
        )

        geo_data = {
            **geocoding_data,
            "highway_type": highway_type,
            "street_importance": street_importance
        }

        set_cache(
            h3_index,
            geo_data
        )

        return {
            "success": True,
            "latitude": data.latitude,
            "longitude": data.longitude,
            **h3_data,
            **geo_data,
            "cache": {
                "hit": False
            }
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
