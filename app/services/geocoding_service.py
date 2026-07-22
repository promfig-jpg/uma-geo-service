import httpx


NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)"
}


async def reverse_geocode(latitude: float, longitude: float):
    # 1. Endereço completo / contexto
    address_params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
        "layer": "address",
    }

    # 2. Objeto de rua
    street_params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "extratags": 1,
        "namedetails": 1,
        "zoom": 17,
        "layer": "address",
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        address_response = await client.get(
            NOMINATIM_URL,
            params=address_params,
            headers=HEADERS,
        )
        address_response.raise_for_status()

        street_response = await client.get(
            NOMINATIM_URL,
            params=street_params,
            headers=HEADERS,
        )
        street_response.raise_for_status()

    data = address_response.json()
    street_data = street_response.json()

    address = data.get("address", {})
    street_address = street_data.get("address", {})

    street_name = (
        street_address.get("road")
        or address.get("road")
        or address.get("pedestrian")
        or address.get("residential")
    )

    return {
        "street": street_name,

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

        # objeto original
        "osm_type": data.get("osm_type"),
        "osm_id": data.get("osm_id"),

        # objeto específico da rua
        "street_osm_type": street_data.get("osm_type"),
        "street_osm_id": street_data.get("osm_id"),
        "street_category": street_data.get("category"),
        "street_type": street_data.get("type"),
        "street_extratags": street_data.get("extratags", {}),
        "street_namedetails": street_data.get("namedetails", {}),
    }
