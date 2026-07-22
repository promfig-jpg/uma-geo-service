from typing import Any

import httpx


WORLDPOP_STAC_SEARCH_URL = "https://api.stac.worldpop.org/search"

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
