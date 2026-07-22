import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def get_way_details(osm_id: int):
    query = f"""
    [out:json];
    way({osm_id});
    out tags;
    """

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            OVERPASS_URL,
            data={"data": query}
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
