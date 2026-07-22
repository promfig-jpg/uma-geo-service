import os
import tempfile
from typing import Any

import httpx
import numpy as np
import rasterio

from app.services.population_service import (
    calculate_audience_score,
    find_population_dataset,
)


async def download_population_raster(
    iso3: str = "BRA",
    year: int = 2025,
) -> tuple[str, dict[str, Any]]:
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


def read_population_at_points(
    raster_path: str,
    points: list[dict],
) -> list[dict]:
    results = []

    with rasterio.open(raster_path) as dataset:
        nodata = dataset.nodata

        coordinates = [
            (
                float(point["longitude"]),
                float(point["latitude"]),
            )
            for point in points
        ]

        sampled = dataset.sample(
            coordinates
        )

        for point, value_array in zip(
            points,
            sampled
        ):
            value = float(
                value_array[0]
            )

            if (
                not np.isfinite(value)
                or (
                    nodata is not None
                    and value == nodata
                )
                or value < 0
            ):
                value = 0.0

            population_estimate = int(
                round(value)
            )

            results.append({
                "h3_index":
                    point["h3_index"],

                "population_estimate":
                    population_estimate,

                "audience_score":
                    calculate_audience_score(
                        population_estimate
                    ),
            })

    return results


async def process_population_points(
    points: list[dict],
    iso3: str = "BRA",
    year: int = 2025,
) -> dict:
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

        results = read_population_at_points(
            raster_path,
            points,
        )

        return {
            "success": True,
            "processed": len(results),
            "year": year,
            "iso3": iso3,
            "dataset_id":
                dataset["dataset_id"],
            "source": "worldpop",
            "results": results,
        }

    finally:
        if (
            raster_path
            and os.path.exists(raster_path)
        ):
            os.remove(raster_path)
