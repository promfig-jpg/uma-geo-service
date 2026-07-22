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
    """
    Procura no catálogo STAC WorldPop um dataset
    de população total para o país e ano indicados.

    Nesta fase apenas localiza o raster.
    A leitura dos pixels será feita depois.
    """

    payload = {
        "datetime": (
            f"{year}-01-01T00:00:00Z/"
            f"{year}-12-31T23:59:59Z"
        ),
        "limit": 100,
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

    iso3 = iso3.upper()
    candidates = []

    for feature in features:
        properties = feature.get("properties", {})
        assets = feature.get("assets", {})

        feature_id = str(
            feature.get("id", "")
        )

        feature_id_upper = feature_id.upper()

        alpha3 = str(
            properties.get(
                "Alpha-3 code",
                ""
            )
        ).upper()

        # Só aceita o país pedido.
        if (
            alpha3 != iso3
            and not feature_id_upper.startswith(
                iso3 + "_"
            )
        ):
            continue

        # Confirma o ano real do produto.
        product_year = properties.get("year")

        if product_year is not None:
            try:
                if int(product_year) != year:
                    continue
            except (TypeError, ValueError):
                continue

        text = (
            feature_id
            + " "
            + str(
                properties.get(
                    "title",
                    ""
                )
            )
            + " "
            + str(
                properties.get(
                    "description",
                    ""
                )
            )
        ).lower()

        # Queremos população total.
        if "population" not in text:
            continue

        # Não queremos density.
        if "density" in text:
            continue

        # Preferimos resolução ~100 m.
        resolution = str(
            properties.get(
                "resolution",
                ""
            )
        ).lower()

        resolution_meters = str(
            properties.get(
                "Resolution (in meters)",
                ""
            )
        ).lower()

        is_100m = (
            "100m" in resolution
            or "100 m" in resolution
            or "100m" in resolution_meters
            or "100 m" in resolution_meters
        )

        if not is_100m:
            continue

        raster_url = None

        for asset in assets.values():
            href = asset.get("href")

            if not href:
                continue

            href_lower = href.lower()

            if (
                ".tif" in href_lower
                or ".tiff" in href_lower
            ):
                raster_url = href
                break

        if not raster_url:
            continue

        candidates.append({
            "dataset_id":
                feature.get("id"),

            "year":
                year,

            "iso3":
                iso3,

            "raster_url":
                raster_url,

            "properties":
                properties,
        })

    if not candidates:
        return None

    # Preferir produto constrained (_CN_).
    candidates.sort(
        key=lambda item:
            0
            if "_CN_" in str(
                item["dataset_id"]
            ).upper()
            else 1
    )

    return candidates[0]
