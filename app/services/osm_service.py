import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Referer": "https://urbanmotoads.com/",
    "Accept": "application/json",
}


async def get_nearby_road(
    latitude: float,
    longitude: float,
    radius: int = 25
):
    query = f"""
    [out:json][timeout:15];
    way
      [highway]
      (around:{radius},{latitude},{longitude});
    out tags center;
    """

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            OVERPASS_URL,
            params={"data": query},
            headers=HEADERS,
        )

        response.raise_for_status()

        data = response.json()
        elements = data.get("elements", [])

        if not elements:
            return {
                "osm_id": None,
                "highway": None,
                "name": None,
                "tags": {},
            }

        # Nesta primeira versão usamos a primeira via encontrada.
        road = elements[0]
        tags = road.get("tags", {})

        return {
            "osm_id": road.get("id"),
            "highway": tags.get("highway"),
            "name": tags.get("name"),
            "tags": tags,
        }
