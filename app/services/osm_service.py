import httpx
import unicodedata


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Referer": "https://urbanmotoads.com/",
    "Accept": "application/json",
}


def normalize_name(value: str | None) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    return value.lower().strip()


def road_score(tags: dict, expected_street: str | None) -> int:
    highway = tags.get("highway", "")
    name = tags.get("name")
    service = tags.get("service")

    score = 0

    expected_normalized = normalize_name(expected_street)
    name_normalized = normalize_name(name)

    if expected_normalized and name_normalized:
        if expected_normalized == name_normalized:
            score += 1000
        elif (
            expected_normalized in name_normalized
            or name_normalized in expected_normalized
        ):
            score += 700

    highway_scores = {
        "motorway": 100,
        "trunk": 90,
        "primary": 80,
        "secondary": 70,
        "tertiary": 60,
        "unclassified": 40,
        "residential": 30,
        "living_street": 20,
        "service": 5,
    }

    score += highway_scores.get(highway, 10)

    if highway == "service":
        score -= 40

    if service == "parking_aisle":
        score -= 100
    elif service == "driveway":
        score -= 60
    elif service == "alley":
        score -= 40

    if name:
        score += 20

    return score


async def get_nearby_road(
    latitude: float,
    longitude: float,
    expected_street: str | None = None,
    radius: int = 30,
):
    query = f"""
    [out:json][timeout:8];
    way
      [highway]
      (around:{radius},{latitude},{longitude});
    out tags;
    """

    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(
                    url,
                    params={"data": query},
                    headers=HEADERS,
                )

                response.raise_for_status()

                elements = response.json().get("elements", [])

                if not elements:
                    continue

                best_road = max(
                    elements,
                    key=lambda road: road_score(
                        road.get("tags", {}),
                        expected_street,
                    ),
                )

                tags = best_road.get("tags", {})

                return {
                    "osm_id": best_road.get("id"),
                    "highway": tags.get("highway"),
                    "name": tags.get("name"),
                    "tags": tags,
                }

        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ):
            continue

    # Overpass indisponível não deve derrubar /geo/enrich
    return {
        "osm_id": None,
        "highway": None,
        "name": expected_street,
        "tags": {},
    }
