import httpx
import unicodedata
from difflib import SequenceMatcher


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
        char
        for char in value
        if not unicodedata.combining(char)
    )

    return value.lower().strip()


def escape_overpass(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )


def name_similarity(
    road_name: str | None,
    expected_street: str | None
) -> float:

    road = normalize_name(road_name)
    expected = normalize_name(expected_street)

    if not road or not expected:
        return 0.0

    if road == expected:
        return 1.0

    return SequenceMatcher(
        None,
        road,
        expected
    ).ratio()


def road_score(
    tags: dict,
    expected_street: str | None
) -> float:

    highway = tags.get("highway")
    name = tags.get("name")
    service = tags.get("service")

    score = 0.0

    # Nome da rua tem prioridade máxima.
    similarity = name_similarity(
        name,
        expected_street
    )

    score += similarity * 1000

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

    score += highway_scores.get(
        highway,
        10
    )

    # Evitar acessos interiores.
    if highway == "service":
        score -= 100

    if service == "parking_aisle":
        score -= 200

    elif service == "driveway":
        score -= 150

    elif service == "alley":
        score -= 100

    if name:
        score += 20

    return score


async def overpass_request(query: str):
    for url in OVERPASS_URLS:

        try:
            async with httpx.AsyncClient(
                timeout=12.0
            ) as client:

                response = await client.get(
                    url,
                    params={"data": query},
                    headers=HEADERS,
                )

                response.raise_for_status()

                data = response.json()

                return data.get(
                    "elements",
                    []
                )

        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.RequestError,
        ):
            continue

    return []


async def get_nearby_road(
    latitude: float,
    longitude: float,
    expected_street: str | None = None,
):

    #
    # 1. PRIMEIRO:
    # procurar especificamente a rua indicada
    # pelo reverse geocoding.
    #
    if expected_street:

        street = escape_overpass(
            expected_street
        )

        exact_query = f"""
        [out:json][timeout:8];
        way
          [highway]
          ["name"="{street}"]
          (around:100,{latitude},{longitude});
        out tags;
        """

        elements = await overpass_request(
            exact_query
        )

        if elements:

            road = elements[0]
            tags = road.get(
                "tags",
                {}
            )

            return {
                "osm_id": road.get("id"),
                "highway": tags.get("highway"),
                "name": tags.get("name"),
                "match_type": "exact_street",
                "tags": tags,
            }

    #
    # 2. FALLBACK:
    # procurar todas as vias próximas.
    #
    nearby_query = f"""
    [out:json][timeout:8];
    way
      [highway]
      (around:40,{latitude},{longitude});
    out tags;
    """

    elements = await overpass_request(
        nearby_query
    )

    if not elements:

        return {
            "osm_id": None,
            "highway": None,
            "name": expected_street,
            "match_type": "not_found",
            "tags": {},
        }

    #
    # Escolher a via com maior correspondência.
    #
    best_road = max(
        elements,
        key=lambda road: road_score(
            road.get("tags", {}),
            expected_street,
        ),
    )

    tags = best_road.get(
        "tags",
        {}
    )

    return {
        "osm_id": best_road.get("id"),
        "highway": tags.get("highway"),
        "name": tags.get("name"),
        "match_type": "nearby_fallback",
        "tags": tags,
    }
