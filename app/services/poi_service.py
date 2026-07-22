import httpx


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Referer": "https://urbanmotoads.com/",
    "Accept": "application/json",
}


async def overpass_request(query: str) -> list:
    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    params={"data": query},
                    headers=HEADERS,
                )

                response.raise_for_status()

                return response.json().get("elements", [])

        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
            ValueError,
        ):
            continue

    return []


def classify_poi(tags: dict) -> str | None:
    amenity = tags.get("amenity")
    shop = tags.get("shop")

    if amenity in {
        "restaurant",
        "cafe",
        "fast_food",
        "bar",
        "pub",
        "food_court",
    }:
        return "restaurant"

    if amenity in {
        "university",
        "college",
        "school",
    }:
        return "university"

    if amenity in {
        "hospital",
        "clinic",
    }:
        return "hospital"

    if shop in {
        "mall",
        "department_store",
    }:
        return "shopping_center"

    return None


async def get_nearby_pois(
    latitude: float,
    longitude: float,
    radius: int = 300,
):
    query = f"""
    [out:json][timeout:10];
    (
      nwr["amenity"~"restaurant|cafe|fast_food|bar|pub|food_court|university|college|school|hospital|clinic"]
         (around:{radius},{latitude},{longitude});

      nwr["shop"~"mall|department_store"]
         (around:{radius},{latitude},{longitude});
    );
    out center tags;
    """

    elements = await overpass_request(query)

    pois = []

    counts = {
        "restaurants_count": 0,
        "universities_count": 0,
        "hospitals_count": 0,
        "shopping_centers_count": 0,
    }

    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        category = classify_poi(tags)

        if not category:
            continue

        key = (
            element.get("type"),
            element.get("id"),
        )

        if key in seen:
            continue

        seen.add(key)

        name = tags.get("name")

        pois.append({
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "name": name,
            "category": category,
            "amenity": tags.get("amenity"),
            "shop": tags.get("shop"),
        })

        if category == "restaurant":
            counts["restaurants_count"] += 1

        elif category == "university":
            counts["universities_count"] += 1

        elif category == "hospital":
            counts["hospitals_count"] += 1

        elif category == "shopping_center":
            counts["shopping_centers_count"] += 1

    return {
        **counts,
        "pois": pois,
        "radius_meters": radius,
    }
