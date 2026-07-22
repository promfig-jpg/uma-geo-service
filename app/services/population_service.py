import math
from typing import Any

import httpx
import numpy as np
import rasterio
from rasterio.windows import from_bounds


HEADERS = {
    "User-Agent": "UrbanMotoAds-GeoService/1.0 (https://urbanmotoads.com)",
    "Accept": "application/json",
}


def calculate_audience_score(
    population: float | int | None
) -> float:
    if population is None:
        return 0.0

    value = float(population)

    if value <= 0:
        return 0.0

    if value <= 25:
        return 10.0

    if value <= 50:
        return 20.0

    if value <= 100:
        return 35.0

    if value <= 200:
        return 50.0

    if value <= 400:
        return 65.0

    if value <= 750:
        return 80.0

    return 100.0


async def find_population_dataset(
    latitude: float,
    longitude: float,
    year: int = 2025,
    iso3: str = "BRA",
) -> dict[str, Any] | None:
    iso3 = iso3.upper()
    iso3_lower = iso3.lower()

    item_id = (
        f"{iso3_lower}_pop_"
        f"{year}_CN_100m_R2025A_v1"
    )

    item_url = (
        f"https://api.stac.worldpop.org/"
        f"collections/{iso3}/items/{item_id}"
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            item_url,
            headers=HEADERS,
        )

        if response.status_code != 200:
            return None

        feature = response.json()

    properties = feature.get(
        "properties",
        {}
    )

    assets = feature.get(
        "assets",
        {}
    )

    raster_url = None

    for asset in assets.values():
        href = asset.get("href")

        if not href:
            continue

        if ".tif" in href.lower():
            raster_url = href
            break

    if not raster_url:
        return None

    return {
        "dataset_id": feature.get(
            "id",
            item_id
        ),
        "year": year,
        "iso3": iso3,
        "country": properties.get("name"),
        "raster_url": raster_url,
        "properties": properties,
    }


def read_population_window(
    raster_url: str,
    latitude: float,
    longitude: float,
    radius_meters: int = 100,
) -> dict[str, float | int]:
    """
    Lê apenas uma pequena janela do raster WorldPop
    em redor do ponto.

    O raster WorldPop representa o número estimado
    de pessoas por pixel.
    """

    lat_delta = (
        radius_meters / 111320.0
    )

    cos_lat = math.cos(
        math.radians(latitude)
    )

    if abs(cos_lat) < 0.000001:
        cos_lat = 0.000001

    lon_delta = (
        radius_meters
        / (
            111320.0
            * cos_lat
        )
    )

    west = longitude - lon_delta
    east = longitude + lon_delta
    south = latitude - lat_delta
    north = latitude + lat_delta

    with rasterio.open(
        raster_url
    ) as dataset:
        window = from_bounds(
            west,
            south,
            east,
            north,
            transform=dataset.transform
        )

        data = dataset.read(
            1,
            window=window,
            masked=True
        )

    if data.size == 0:
        return {
            "population_estimate": 0,
            "pixels_used": 0,
        }

    valid_data = data.compressed()

    if valid_data.size == 0:
        return {
            "population_estimate": 0,
            "pixels_used": 0,
        }

    valid_data = valid_data[
        np.isfinite(valid_data)
    ]

    valid_data = valid_data[
        valid_data >= 0
    ]

    if valid_data.size == 0:
        return {
            "population_estimate": 0,
            "pixels_used": 0,
        }

    population = float(
        valid_data.sum()
    )

    return {
        "population_estimate":
            int(round(population)),

        "pixels_used":
            int(valid_data.size),
    }


async def get_population_estimate(
    latitude: float,
    longitude: float,
    year: int = 2025,
    iso3: str = "BRA",
) -> dict:
    dataset = await find_population_dataset(
        latitude,
        longitude,
        year=year,
        iso3=iso3
    )

    if not dataset:
        return {
            "success": False,
            "population_estimate": None,
            "audience_score": 0.0,
            "pixels_used": 0,
            "year": year,
            "iso3": iso3,
            "dataset_id": None,
            "source": None,
        }

    population = read_population_window(
        raster_url=dataset["raster_url"],
        latitude=latitude,
        longitude=longitude,
        radius_meters=100,
    )

    estimate = population[
        "population_estimate"
    ]

    return {
        "success": True,

        "population_estimate":
            estimate,

        "audience_score":
            calculate_audience_score(
                estimate
            ),

        "pixels_used":
            population["pixels_used"],

        "year":
            year,

        "iso3":
            iso3,

        "dataset_id":
            dataset["dataset_id"],

        "source":
            "worldpop",
    }
