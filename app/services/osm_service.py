import httpx
import unicodedata


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

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

    # Preferência máxima pela rua identificada pelo geocoding
    if expected_normalized and name_normalized:
        if expected_normalized == name_normalized:
            score += 1000
        elif (
            expected_normalized in name_normalized
            or name_normalized in expected_normalized
        ):
            score += 700

    # Peso pela importância real da via
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

    # Penalizações para acessos internos
    if highway == "service":
        score -= 40

    if service == "parking_aisle":
        score -= 100

    if service == "driveway":
        score -= 60

    if service == "alley":
        score -= 40

    # Uma via com nome é normalmente mais relevante
    if name:
        score += 20

    return score


async def get_nearby_road(
    latitude: float,
    longitude: float,
    expected_street: str | None = None,
    radius: int = 40,
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

        best_road = max(
            elements,
            key=lambda road: road_score(
                road.get("tags", {}),
                expected_street
            )
        )

        tags = best_road.get("tags", {})

        return {
            "osm_id": best_road.get("id"),
            "highway": tags.get("highway"),
            "name": tags.get("name"),
            "tags": tags,
        }
