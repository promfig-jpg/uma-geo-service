import math
import unicodedata
from difflib import SequenceMatcher

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


# ---------------------------------------------------------
# Normalização de nomes
# ---------------------------------------------------------

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


def name_similarity(
    value1: str | None,
    value2: str | None
) -> float:

    name1 = normalize_name(value1)
    name2 = normalize_name(value2)

    if not name1 or not name2:
        return 0.0

    if name1 == name2:
        return 1.0

    return SequenceMatcher(
        None,
        name1,
        name2
    ).ratio()


def street_name_match(
    tags: dict,
    expected_street: str | None
) -> float:
    """
    Compara a rua esperada com vários nomes OSM:
    name, alt_name, official_name, short_name.
    """

    if not expected_street:
        return 0.0

    possible_names = [
        tags.get("name"),
        tags.get("alt_name"),
        tags.get("official_name"),
        tags.get("short_name"),
    ]

    best_similarity = 0.0

    for road_name in possible_names:
        similarity = name_similarity(
            road_name,
            expected_street
        )

        if similarity > best_similarity:
            best_similarity = similarity

    return best_similarity


# ---------------------------------------------------------
# Distância ponto -> segmento
# ---------------------------------------------------------

def latlon_to_xy(
    latitude: float,
    longitude: float,
    reference_latitude: float,
    reference_longitude: float
) -> tuple[float, float]:
    """
    Converte latitude/longitude em metros relativamente
    ao ponto GPS de referência.

    Para distâncias pequenas (< algumas centenas de metros)
    esta aproximação é suficientemente precisa.
    """

    earth_radius = 6371000.0

    lat_rad = math.radians(reference_latitude)

    x = (
        math.radians(longitude - reference_longitude)
        * earth_radius
        * math.cos(lat_rad)
    )

    y = (
        math.radians(latitude - reference_latitude)
        * earth_radius
    )

    return x, y


def point_to_segment_distance(
    ax: float,
    ay: float,
    bx: float,
    by: float
) -> float:
    """
    Distância do ponto GPS (0,0) ao segmento A-B.
    """

    dx = bx - ax
    dy = by - ay

    segment_length_squared = dx * dx + dy * dy

    if segment_length_squared == 0:
        return math.sqrt(
            ax * ax + ay * ay
        )

    t = -(
        ax * dx + ay * dy
    ) / segment_length_squared

    t = max(
        0.0,
        min(1.0, t)
    )

    closest_x = ax + t * dx
    closest_y = ay + t * dy

    return math.sqrt(
        closest_x * closest_x
        + closest_y * closest_y
    )


def distance_to_way(
    latitude: float,
    longitude: float,
    geometry: list
) -> float | None:
    """
    Calcula a distância mínima entre o GPS e
    toda a geometria da estrada.
    """

    if not geometry:
        return None

    points = []

    for point in geometry:

        point_lat = point.get("lat")
        point_lon = point.get("lon")

        if point_lat is None or point_lon is None:
            continue

        x, y = latlon_to_xy(
            point_lat,
            point_lon,
            latitude,
            longitude
        )

        points.append((x, y))

    if not points:
        return None

    if len(points) == 1:
        x, y = points[0]

        return math.sqrt(
            x * x + y * y
        )

    minimum_distance = float("inf")

    for index in range(len(points) - 1):

        ax, ay = points[index]
        bx, by = points[index + 1]

        distance = point_to_segment_distance(
            ax,
            ay,
            bx,
            by
        )

        minimum_distance = min(
            minimum_distance,
            distance
        )

    return minimum_distance


# ---------------------------------------------------------
# Classificação das vias
# ---------------------------------------------------------

def is_internal_service_road(tags: dict) -> bool:
    """
    Identifica acessos que normalmente não devem
    representar a rua onde a moto está a circular.
    """

    if tags.get("highway") != "service":
        return False

    service_type = tags.get("service")

    return service_type in {
        "parking_aisle",
        "driveway",
        "alley",
        "drive-through",
    }


def is_normal_road(tags: dict) -> bool:
    """
    Vias normalmente relevantes para circulação urbana.
    """

    highway = tags.get("highway")

    return highway in {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "living_street",
    }


# ---------------------------------------------------------
# Overpass
# ---------------------------------------------------------

async def overpass_request(query: str) -> list:
    for url in OVERPASS_URLS:

        try:
            async with httpx.AsyncClient(
                timeout=15.0
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
            ValueError,
        ):
            continue

    return []


# ---------------------------------------------------------
# Encontrar estrada correspondente ao GPS
# ---------------------------------------------------------

async def get_nearby_road(
    latitude: float,
    longitude: float,
    expected_street: str | None = None,
    radius: int = 60,
):

    query = f"""
    [out:json][timeout:10];
    way
      [highway]
      (around:{radius},{latitude},{longitude});
    out tags geom;
    """

    elements = await overpass_request(
        query
    )

    candidates = []

    for road in elements:

        tags = road.get(
            "tags",
            {}
        )

        geometry = road.get(
            "geometry",
            []
        )

        distance = distance_to_way(
            latitude,
            longitude,
            geometry
        )

        if distance is None:
            continue

        similarity = street_name_match(
            tags,
            expected_street
        )

        candidates.append({
            "osm_id": road.get("id"),
            "highway": tags.get("highway"),
            "name": tags.get("name"),
            "distance_m": round(distance, 2),
            "name_similarity": round(similarity, 3),
            "tags": tags,
        })

    if not candidates:

        return {
            "osm_id": None,
            "highway": None,
            "name": expected_street,
            "distance_m": None,
            "match_type": "not_found",
            "tags": {},
        }

    # -----------------------------------------------------
    # 1. Prioridade máxima:
    #    rua com nome igual ou muito semelhante ao
    #    Nominatim.
    # -----------------------------------------------------

    matching_streets = [
        road
        for road in candidates
        if road["name_similarity"] >= 0.85
    ]

    if matching_streets:

        best_road = min(
            matching_streets,
            key=lambda road: road["distance_m"]
        )

        best_road["match_type"] = "street_name_geometry"

        return best_road

    # -----------------------------------------------------
    # 2. Não havendo correspondência do nome:
    #    excluir estacionamentos, driveways, etc.
    # -----------------------------------------------------

    normal_roads = [
        road
        for road in candidates
        if is_normal_road(
            road["tags"]
        )
    ]

    if normal_roads:

        best_road = min(
            normal_roads,
            key=lambda road: road["distance_m"]
        )

        best_road["match_type"] = "nearest_road"

        return best_road

    # -----------------------------------------------------
    # 3. Último recurso:
    #    qualquer highway, mas evitar acessos internos
    # -----------------------------------------------------

    usable_roads = [
        road
        for road in candidates
        if not is_internal_service_road(
            road["tags"]
        )
    ]

    if usable_roads:

        best_road = min(
            usable_roads,
            key=lambda road: road["distance_m"]
        )

        best_road["match_type"] = "nearest_fallback"

        return best_road

    # -----------------------------------------------------
    # 4. Último fallback absoluto
    # -----------------------------------------------------

    best_road = min(
        candidates,
        key=lambda road: road["distance_m"]
    )

    best_road["match_type"] = "service_fallback"

    return best_road
