import httpx
import h3

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
    def get_h3_bbox(
    h3_index: str
) -> tuple[
    float,
    float,
    float,
    float,
]:
    """
    Retorna:
        south,
        west,
        north,
        east
    """

    if not h3.is_valid_cell(h3_index):
        raise ValueError(
            "Invalid H3 index."
        )

    boundary = h3.cell_to_boundary(
        h3_index
    )

    latitudes = [
        float(point[0])
        for point in boundary
    ]

    longitudes = [
        float(point[1])
        for point in boundary
    ]

    return (
        min(latitudes),
        min(longitudes),
        max(latitudes),
        max(longitudes),
    )


async def get_h3_pois(
    h3_index: str
) -> dict:
    """
    Obtém POIs que estão realmente dentro
    da célula H3.
    """

    if not h3.is_valid_cell(h3_index):
        raise ValueError(
            "Invalid H3 index."
        )

    resolution = h3.get_resolution(
        h3_index
    )

    south, west, north, east = (
        get_h3_bbox(
            h3_index
        )
    )

    query = f"""
    [out:json][timeout:25];
    (
      nwr["amenity"~"restaurant|cafe|fast_food|bar|pub|food_court|university|college|school|hospital|clinic|cinema"]
        ({south},{west},{north},{east});

      nwr["shop"~"mall|department_store|supermarket"]
        ({south},{west},{north},{east});

      nwr["leisure"~"fitness_centre|sports_centre"]
        ({south},{west},{north},{east});

      nwr["tourism"~"hotel|hostel|attraction|museum"]
        ({south},{west},{north},{east});
    );
    out center tags;
    """

    result = await overpass_request(
        query
    )

    if not result["success"]:
        return {
            "success": False,
            "overpass_available": False,
            "h3_index": h3_index,
            "resolution": resolution,
            "poi_count": 0,
            "counts": {},
            "pois": [],
            "source": None,
            "errors": result["errors"],
        }

    counts = {
        "restaurants": 0,
        "universities": 0,
        "schools": 0,
        "hospitals": 0,
        "shopping_centers": 0,
        "cinemas": 0,
        "supermarkets": 0,
        "gyms": 0,
        "hotels": 0,
        "tourism": 0,
    }

    pois = []
    seen = set()

    for element in result["elements"]:
        tags = element.get(
            "tags",
            {}
        )

        element_type = element.get(
            "type"
        )

        element_id = element.get(
            "id"
        )

        key = (
            element_type,
            element_id,
        )

        if key in seen:
            continue

        seen.add(key)

        latitude = element.get(
            "lat"
        )

        longitude = element.get(
            "lon"
        )

        if (
            latitude is None
            or longitude is None
        ):
            center = element.get(
                "center",
                {}
            )

            latitude = center.get(
                "lat"
            )

            longitude = center.get(
                "lon"
            )

        if (
            latitude is None
            or longitude is None
        ):
            continue

        latitude = float(latitude)
        longitude = float(longitude)

        /*
         * Este filtro é fundamental:
         * a query usa uma bounding box retangular,
         * mas só queremos POIs dentro do hexágono H3.
         */
        poi_h3 = h3.latlng_to_cell(
            latitude,
            longitude,
            resolution
        )

        if poi_h3 != h3_index:
            continue

        category = classify_h3_poi(
            tags
        )

        if category is None:
            continue

        counts[category] += 1

        pois.append({
            "osm_type":
                element_type,

            "osm_id":
                element_id,

            "name":
                tags.get("name"),

            "category":
                category,

            "amenity":
                tags.get("amenity"),

            "shop":
                tags.get("shop"),

            "leisure":
                tags.get("leisure"),

            "tourism":
                tags.get("tourism"),

            "latitude":
                latitude,

            "longitude":
                longitude,
        })

    return {
        "success": True,
        "overpass_available": True,

        "h3_index":
            h3_index,

        "resolution":
            resolution,

        "poi_count":
            len(pois),

        "counts":
            counts,

        "pois":
            pois,

        "source":
            result["source"],

        "errors":
            [],
    }


def classify_h3_poi(
    tags: dict
) -> str | None:
    amenity = tags.get(
        "amenity"
    )

    shop = tags.get(
        "shop"
    )

    leisure = tags.get(
        "leisure"
    )

    tourism = tags.get(
        "tourism"
    )

    if amenity in {
        "restaurant",
        "cafe",
        "fast_food",
        "bar",
        "pub",
        "food_court",
    }:
        return "restaurants"

    if amenity in {
        "university",
        "college",
    }:
        return "universities"

    if amenity == "school":
        return "schools"

    if amenity in {
        "hospital",
        "clinic",
    }:
        return "hospitals"

    if amenity == "cinema":
        return "cinemas"

    if shop in {
        "mall",
        "department_store",
    }:
        return "shopping_centers"

    if shop == "supermarket":
        return "supermarkets"

    if leisure in {
        "fitness_centre",
        "sports_centre",
    }:
        return "gyms"

    if tourism in {
        "hotel",
        "hostel",
    }:
        return "hotels"

    if tourism in {
        "attraction",
        "museum",
    }:
        return "tourism"

    return None
