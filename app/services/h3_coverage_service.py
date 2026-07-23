import math
from typing import Any

import h3


def polygon_to_h3_coverage(
    coordinates: list[list[float]],
    resolution: int = 9,
) -> list[dict[str, Any]]:
    """
    Converte um polígono GeoJSON simples em células H3.

    coordinates:
        [
            [longitude, latitude],
            [longitude, latitude],
            ...
        ]
    """

    if resolution < 0 or resolution > 15:
        raise ValueError(
            "H3 resolution must be between 0 and 15."
        )

    if not coordinates or len(coordinates) < 3:
        raise ValueError(
            "Polygon must contain at least 3 coordinates."
        )

    cleaned_coordinates = []

    for coordinate in coordinates:
        if (
            not isinstance(
                coordinate,
                (list, tuple)
            )
            or len(coordinate) < 2
        ):
            raise ValueError(
                "Invalid polygon coordinate."
            )

        longitude = float(
            coordinate[0]
        )

        latitude = float(
            coordinate[1]
        )

        if latitude < -90 or latitude > 90:
            raise ValueError(
                f"Invalid latitude: {latitude}"
            )

        if longitude < -180 or longitude > 180:
            raise ValueError(
                f"Invalid longitude: {longitude}"
            )

        cleaned_coordinates.append([
            longitude,
            latitude,
        ])

    if (
        cleaned_coordinates[0]
        != cleaned_coordinates[-1]
    ):
        cleaned_coordinates.append(
            cleaned_coordinates[0]
        )

    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [
            cleaned_coordinates
        ],
    }

    cells = h3.geo_to_cells(
        geojson_polygon,
        resolution
    )

    return _cells_to_results(
        cells,
        resolution
    )


def geojson_to_h3_coverage(
    geometry: dict[str, Any],
    resolution: int = 9,
) -> list[dict[str, Any]]:
    """
    Converte uma geometria GeoJSON Polygon
    ou MultiPolygon em cobertura H3.
    """

    if not geometry:
        raise ValueError(
            "Geometry is required."
        )

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not coordinates:
        raise ValueError(
            "Geometry coordinates are required."
        )

    all_cells = set()

    if geometry_type == "Polygon":
        polygon = {
            "type": "Polygon",
            "coordinates": coordinates,
        }

        cells = h3.geo_to_cells(
            polygon,
            resolution
        )

        all_cells.update(cells)

    elif geometry_type == "MultiPolygon":
        for polygon_coordinates in coordinates:
            polygon = {
                "type": "Polygon",
                "coordinates":
                    polygon_coordinates,
            }

            cells = h3.geo_to_cells(
                polygon,
                resolution
            )

            all_cells.update(cells)

    else:
        raise ValueError(
            "Only Polygon and MultiPolygon are supported."
        )

    return _cells_to_results(
        all_cells,
        resolution
    )


def radius_to_h3_coverage(
    latitude: float,
    longitude: float,
    radius_meters: float,
    resolution: int = 9,
    polygon_points: int = 72,
) -> list[dict[str, Any]]:
    """
    Converte uma zona circular definida por:
        latitude
        longitude
        radius_meters

    num polígono aproximado e depois em células H3.

    polygon_points=72 cria um círculo suficientemente
    preciso para zonas operacionais urbanas.
    """

    latitude = float(latitude)
    longitude = float(longitude)
    radius_meters = float(radius_meters)

    if latitude < -90 or latitude > 90:
        raise ValueError(
            "Invalid latitude."
        )

    if longitude < -180 or longitude > 180:
        raise ValueError(
            "Invalid longitude."
        )

    if radius_meters <= 0:
        raise ValueError(
            "radius_meters must be greater than zero."
        )

    if resolution < 0 or resolution > 15:
        raise ValueError(
            "H3 resolution must be between 0 and 15."
        )

    if polygon_points < 12:
        polygon_points = 12

    coordinates = []

    earth_radius_m = 6371008.8

    lat_rad = math.radians(
        latitude
    )

    lon_rad = math.radians(
        longitude
    )

    angular_distance = (
        radius_meters
        / earth_radius_m
    )

    for i in range(
        polygon_points
    ):
        bearing = (
            2.0
            * math.pi
            * i
            / polygon_points
        )

        sin_lat = (
            math.sin(lat_rad)
            * math.cos(
                angular_distance
            )
            + math.cos(lat_rad)
            * math.sin(
                angular_distance
            )
            * math.cos(bearing)
        )

        point_lat = math.asin(
            sin_lat
        )

        y = (
            math.sin(bearing)
            * math.sin(
                angular_distance
            )
            * math.cos(lat_rad)
        )

        x = (
            math.cos(
                angular_distance
            )
            - math.sin(lat_rad)
            * math.sin(point_lat)
        )

        point_lon = (
            lon_rad
            + math.atan2(
                y,
                x
            )
        )

        point_lat_deg = (
            math.degrees(
                point_lat
            )
        )

        point_lon_deg = (
            math.degrees(
                point_lon
            )
        )

        # Normaliza longitude para -180..180
        point_lon_deg = (
            (
                point_lon_deg
                + 180.0
            )
            % 360.0
        ) - 180.0

        coordinates.append([
            point_lon_deg,
            point_lat_deg,
        ])

    if (
        coordinates[0]
        != coordinates[-1]
    ):
        coordinates.append(
            coordinates[0]
        )

    return polygon_to_h3_coverage(
        coordinates=coordinates,
        resolution=resolution,
    )


def _cells_to_results(
    cells,
    resolution: int,
) -> list[dict[str, Any]]:
    """
    Converte índices H3 numa resposta uniforme.
    """

    results = []

    for h3_index in sorted(
        cells
    ):
        latitude_center, longitude_center = (
            h3.cell_to_latlng(
                h3_index
            )
        )

        results.append({
            "h3_index":
                h3_index,

            "resolution":
                resolution,

            "latitude_center":
                float(
                    latitude_center
                ),

            "longitude_center":
                float(
                    longitude_center
                ),
        })

    return results
