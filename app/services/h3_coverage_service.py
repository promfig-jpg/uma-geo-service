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

    # Fecha automaticamente o polígono.
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

    results = []

    for h3_index in sorted(cells):
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
                float(latitude_center),

            "longitude_center":
                float(longitude_center),
        })

    return results


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

    all_cells = {}

    if geometry_type == "Polygon":
        polygon = {
            "type": "Polygon",
            "coordinates": coordinates,
        }

        cells = h3.geo_to_cells(
            polygon,
            resolution
        )

        for h3_index in cells:
            all_cells[h3_index] = True

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

            for h3_index in cells:
                all_cells[h3_index] = True

    else:
        raise ValueError(
            "Only Polygon and MultiPolygon are supported."
        )

    results = []

    for h3_index in sorted(
        all_cells.keys()
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
                float(latitude_center),

            "longitude_center":
                float(longitude_center),
        })

    return results
