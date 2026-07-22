import httpx


OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Referer": "https://urbanmotoads.com/",
    "Accept": "application/json",
}


async def overpass_request(query: str) -> dict:
    errors = []

    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(
                    url,
                    data={"data": query},
                    headers=HEADERS,
                )

                response.raise_for_status()

                return {
                    "success": True,
                    "source": url,
                    "elements": response.json().get("elements", []),
                    "errors": [],
                }

        except Exception as error:
            errors.append(
                f"{url}: {type(error).__name__}"
            )

    return {
        "success": False,
        "source": None,
        "elements": [],
        "errors": errors,
    }


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
    }:
        return "university"

    if amenity == "school":
        return "school"

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
    [out:json][timeout:20];
    (
      nwr["amenity"~"restaurant|cafe|fast_food|bar|pub|food_court|university|college|school|hospital|clinic"]
        (around:{radius},{latitude},{longitude});

      nwr["shop"~"mall|department_store"]
        (around:{radius},{latitude},{longitude});
    );
    out center tags;
    """

    result = await overpass_request(query)

    if not result["success"]:
        return {
            "success": False,
            "overpass_available": False,
            "restaurants_count": 0,
            "universities_count": 0,
            "schools_count": 0,
            "hospitals_count": 0,
            "shopping_centers_count": 0,
            "pois": [],
            "radius_meters": radius,
            "source": None,
            "errors": result["errors"],
        }

    elements = result["elements"]

    counts = {
        "restaurants_count": 0,
        "universities_count": 0,
        "schools_count": 0,
        "hospitals_count": 0,
        "shopping_centers_count": 0,
    }

    pois = []
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

        pois.append({
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "name": tags.get("name"),
            "category": category,
            "amenity": tags.get("amenity"),
            "shop": tags.get("shop"),
        })

        if category == "restaurant":
            counts["restaurants_count"] += 1
        elif category == "university":
            counts["universities_count"] += 1
        elif category == "school":
            counts["schools_count"] += 1
        elif category == "hospital":
            counts["hospitals_count"] += 1
        elif category == "shopping_center":
            counts["shopping_centers_count"] += 1

    return {
        "success": True,
        "overpass_available": True,
        **counts,
        "pois": pois,
        "radius_meters": radius,
        "source": result["source"],
        "errors": [],
    }
