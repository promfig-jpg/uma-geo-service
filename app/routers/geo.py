from fastapi import APIRouter, HTTPException

from app.models.geo import GeoRequest
from app.services.h3_service import coordinates_to_h3
from app.services.geocoding_service import reverse_geocode
from app.services.osm_service import get_nearby_road
from app.services.street_service import calculate_street_importance


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

        highway_type = None
        street_importance = 0
        osm_way = None

    osm_way = await get_nearby_road(
    data.latitude,
    data.longitude
)

highway_type = osm_way.get("highway")

street_importance = calculate_street_importance(
    highway_type
)

        return {
            "success": True,
            "latitude": data.latitude,
            "longitude": data.longitude,
            **h3_data,
            **geocoding_data,
            "highway_type": highway_type,
            "street_importance": street_importance,
            "osm_way": osm_way
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
