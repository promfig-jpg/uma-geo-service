import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0"
}


async def reverse_geocode(latitude: float, longitude: float):
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            NOMINATIM_URL,
            params=params,
            headers=HEADERS,
        )

        response.raise_for_status()

        data = response.json()
        address = data.get("address", {})

        return {
            "street": (
                address.get("road")
                or address.get("pedestrian")
                or address.get("residential")
            ),
            "neighbourhood": (
                address.get("neighbourhood")
                or address.get("suburb")
            ),
            "city": (
                address.get("city")
                or address.get("town")
                or address.get("municipality")
            ),
            "state": address.get("state"),
            "postcode": address.get("postcode"),
            "country": address.get("country"),
            "country_code": address.get("country_code"),
            "display_name": data.get("display_name"),
            "osm_type": data.get("osm_type"),
            "osm_id": data.get("osm_id"),
        }
