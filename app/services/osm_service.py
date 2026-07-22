import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Referer": "https://urbanmotoads.com/",
    "Accept": "application/json",
}


async def get_way_details(osm_id: int):
    query = f"""
    [out:json][timeout:15];
    way({osm_id});
    out tags;
    """

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            OVERPASS_URL,
            params={"data": query},
            headers=HEADERS
        )

        response.raise_for_status()

        data = response.json()
        elements = data.get("elements", [])

        if not elements:
            return {
                "highway": None,
                "name": None,
                "tags": {}
            }

        tags = elements[0].get("tags", {})

        return {
            "highway": tags.get("highway"),
            "name": tags.get("name"),
            "tags": tags
        }
