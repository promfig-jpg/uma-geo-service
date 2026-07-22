STREET_IMPORTANCE_MAP = {
    "motorway": 5,
    "motorway_link": 5,
    "trunk": 5,
    "trunk_link": 5,

    "primary": 4,
    "primary_link": 4,

    "secondary": 3,
    "secondary_link": 3,

    "tertiary": 2,
    "tertiary_link": 2,
    "unclassified": 2,

    "residential": 1,
    "living_street": 1,
    "service": 1,
}


def calculate_street_importance(highway_type: str | None) -> int:
    if not highway_type:
        return 0

    return STREET_IMPORTANCE_MAP.get(highway_type, 1)
