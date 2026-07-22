import math
import os
import tempfile
from typing import Any

import h3
import httpx
import numpy as np
import rasterio

from rasterio.windows import Window, from_bounds
from shapely.geometry import Polygon, box

from app.services.population_service import (
    calculate_audience_score,
    find_population_dataset,
)


async def download_population_raster(
    iso3: str = "BRA",
    year: int = 2025,
) -> tuple[str, dict[str, Any]]:
    """
    Descarrega temporariamente o raster WorldPop
    correspondente ao país/ano.
    """

    dataset = await find_population_dataset(
        latitude=0,
        longitude=0,
        year=year,
        iso3=iso3,
    )

    if not dataset:
        raise RuntimeError(
            f"WorldPop dataset not found for {iso3}/{year}"
        )

    raster_url = dataset["raster_url"]

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".tif",
        delete=False,
    )

    temp_path = temp_file.name
    temp_file.close()

    try:
        async with httpx.AsyncClient(
            timeout=None,
            follow_redirects=True,
        ) as client:
            async with client.stream(
                "GET",
                raster_url,
                headers={
                    "User-Agent":
                        "UrbanMotoAds-GeoService/1.0"
                },
            ) as response:
                response.raise_for_status()

                with open(temp_path, "wb") as file:
                    async for chunk in response.aiter_bytes(
                        chunk_size=1024 * 1024
                    ):
                        file.write(chunk)

        return temp_path, dataset

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise


def h3_to_polygon(
    h3_index: str,
) -> Polygon:
    """
    Converte uma célula H3 num polígono Shapely.

    h3.cell_to_boundary devolve:
        latitude, longitude

    Shapely utiliza:
        longitude, latitude
    """

    boundary = h3.cell_to_boundary(
        h3_index
    )

    coordinates = [
        (
            float(longitude),
            float(latitude),
        )
        for latitude, longitude in boundary
    ]

    return Polygon(coordinates)


def get_safe_window(
    dataset,
    polygon: Polygon,
) -> Window:
    """
    Obtém uma janela raster que cobre completamente
    o polígono H3.
    """

    min_x, min_y, max_x, max_y = (
        polygon.bounds
    )

    raw_window = from_bounds(
        min_x,
        min_y,
        max_x,
        max_y,
        transform=dataset.transform,
    )

    col_start = math.floor(
        raw_window.col_off
    )

    row_start = math.floor(
        raw_window.row_off
    )

    col_end = math.ceil(
        raw_window.col_off
        + raw_window.width
    )

    row_end = math.ceil(
        raw_window.row_off
        + raw_window.height
    )

    # Garante que a janela permanece dentro do raster.
    col_start = max(
        0,
        col_start,
    )

    row_start = max(
        0,
        row_start,
    )

    col_end = min(
        dataset.width,
        col_end,
    )

    row_end = min(
        dataset.height,
        row_end,
    )

    return Window(
        col_off=col_start,
        row_off=row_start,
        width=max(
            0,
            col_end - col_start,
        ),
        height=max(
            0,
            row_end - row_start,
        ),
    )


def calculate_h3_population(
    dataset,
    h3_index: str,
) -> dict:
    """
    Calcula a população WorldPop estimada dentro
    de uma célula H3.

    Para cada pixel WorldPop:
      população do pixel
          x
      fração da área do pixel que intersecta o H3

    O resultado é depois somado.
    """

    polygon = h3_to_polygon(
        h3_index
    )

    if polygon.is_empty:
        return {
            "population_estimate": 0,
            "population_raw": 0.0,
            "pixels_intersected": 0,
            "pixels_equivalent": 0.0,
        }

    window = get_safe_window(
        dataset,
        polygon,
    )

    if (
        window.width <= 0
        or window.height <= 0
    ):
        return {
            "population_estimate": 0,
            "population_raw": 0.0,
            "pixels_intersected": 0,
            "pixels_equivalent": 0.0,
        }

    data = dataset.read(
        1,
        window=window,
        masked=True,
    )

    window_transform = (
        dataset.window_transform(
            window
        )
    )

    nodata = dataset.nodata

    population_total = 0.0
    pixels_intersected = 0
    pixels_equivalent = 0.0

    rows, cols = data.shape

    for row in range(rows):
        for col in range(cols):
            value = data[row, col]

            if np.ma.is_masked(value):
                continue

            value = float(value)

            if not np.isfinite(value):
                continue

            if value < 0:
                continue

            if (
                nodata is not None
                and value == nodata
            ):
                continue

            # Limites geográficos deste pixel.
            x_left, y_top = (
                rasterio.transform.xy(
                    window_transform,
                    row,
                    col,
                    offset="ul",
                )
            )

            x_right, y_bottom = (
                rasterio.transform.xy(
                    window_transform,
                    row,
                    col,
                    offset="lr",
                )
            )

            pixel_polygon = box(
                min(x_left, x_right),
                min(y_bottom, y_top),
                max(x_left, x_right),
                max(y_bottom, y_top),
            )

            if not polygon.intersects(
                pixel_polygon
            ):
                continue

            intersection = polygon.intersection(
                pixel_polygon
            )

            if intersection.is_empty:
                continue

            pixel_area = (
                pixel_polygon.area
            )

            if pixel_area <= 0:
                continue

            fraction = (
                intersection.area
                / pixel_area
            )

            fraction = max(
                0.0,
                min(
                    1.0,
                    fraction,
                ),
            )

            if fraction <= 0:
                continue

            population_total += (
                value * fraction
            )

            pixels_intersected += 1
            pixels_equivalent += fraction

    return {
        "population_estimate":
            int(round(population_total)),

        "population_raw":
            round(
                population_total,
                4,
            ),

        "pixels_intersected":
            pixels_intersected,

        "pixels_equivalent":
            round(
                pixels_equivalent,
                4,
            ),
    }


def read_population_for_h3_cells(
    raster_path: str,
    points: list[dict],
) -> list[dict]:
    """
    Processa várias células H3 utilizando
    o mesmo raster já descarregado.
    """

    results = []

    with rasterio.open(
        raster_path
    ) as dataset:

        for point in points:
            h3_index = str(
                point["h3_index"]
            )

            population = (
                calculate_h3_population(
                    dataset,
                    h3_index,
                )
            )

            estimate = (
                population[
                    "population_estimate"
                ]
            )

            results.append({
                "h3_index":
                    h3_index,

                "population_estimate":
                    estimate,

                "population_raw":
                    population[
                        "population_raw"
                    ],

                "audience_score":
                    calculate_audience_score(
                        estimate
                    ),

                "pixels_intersected":
                    population[
                        "pixels_intersected"
                    ],

                "pixels_equivalent":
                    population[
                        "pixels_equivalent"
                    ],
            })

    return results


async def process_population_points(
    points: list[dict],
    iso3: str = "BRA",
    year: int = 2025,
) -> dict:
    """
    Descarrega o raster uma vez e processa
    todas as células H3 recebidas no batch.
    """

    if not points:
        return {
            "success": True,
            "processed": 0,
            "results": [],
        }

    raster_path = None

    try:
        raster_path, dataset = (
            await download_population_raster(
                iso3=iso3,
                year=year,
            )
        )

        results = (
            read_population_for_h3_cells(
                raster_path,
                points,
            )
        )

        return {
            "success": True,

            "processed":
                len(results),

            "year":
                year,

            "iso3":
                iso3,

            "dataset_id":
                dataset[
                    "dataset_id"
                ],

            "source":
                "worldpop",

            "method":
                "h3_polygon_weighted_pixels",

            "results":
                results,
        }

    finally:
        if (
            raster_path
            and os.path.exists(
                raster_path
            )
        ):
            os.remove(
                raster_path
            )
