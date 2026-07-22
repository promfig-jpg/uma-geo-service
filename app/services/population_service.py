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
    year: int = 2025
) -> dict[str, Any] | None:
    """
    Procura no catálogo STAC WorldPop um dataset
    recente que cubra o ponto solicitado.

    Nesta fase apenas localizamos o raster.
    A leitura dos pixels será adicionada no passo seguinte.
    """

    payload = {
        "bbox": [
            longitude,
            latitude,
            longitude,
            latitude,
        ],
        "datetime": f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z",
        "limit": 20,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            WORLDPOP_STAC_SEARCH_URL,
            json=payload,
            headers=HEADERS,
        )

        response.raise_for_status()

        data = response.json()

    features = data.get("features", [])

    if not features:
        return None

    for feature in features:
        properties = feature.get("properties", {})
        assets = feature.get("assets", {})

        text = (
            str(feature.get("id", ""))
            + " "
            + str(properties)
        ).lower()

        # Queremos população total, não idade/sexo/densidade.
        if "population" not in text:
            continue

        if "density" in text:
            continue

        raster_url = None

        for asset in assets.values():
            href = asset.get("href")

            if not href:
                continue

            if ".tif" in href.lower():
                raster_url = href
                break

        if raster_url:
            return {
                "dataset_id": feature.get("id"),
                "year": year,
                "raster_url": raster_url,
                "properties": properties,
            }

    return None
