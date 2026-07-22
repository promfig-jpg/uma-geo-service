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
    Procura no catálogo STAC WorldPop um raster
    de população total para o país e ano indicados.
    """

    payload = {
        "limit": 500,
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            WORLDPOP_STAC_SEARCH_URL,
            json=payload,
            headers=HEADERS,
        )

        response.raise_for_status()
        data = response.json()

    features = data.get("features", [])

    iso3 = iso3.upper()

    candidates = []

    for feature in features:
        feature_id = str(
            feature.get("id", "")
        )

        properties = feature.get(
            "properties",
            {}
        )

        assets = feature.get(
            "assets",
            {}
        )

        alpha3 = str(
            properties.get(
                "Alpha-3 code",
                ""
            )
        ).upper()

        country_name = str(
            properties.get(
                "name",
                ""
            )
        ).lower()

        product_year = properties.get(
            "year"
        )

        title = str(
            properties.get(
                "title",
                ""
            )
        ).lower()

        description = str(
            properties.get(
                "description",
                ""
            )
        ).lower()

        combined_text = (
            feature_id
            + " "
            + title
            + " "
            + description
        ).lower()

        # País.
        is_country_match = (
            alpha3 == iso3
            or "brazil" in country_name
            or "brazil" in title
            or feature_id.lower().startswith(
                iso3.lower() + "_"
            )
        )

        if not is_country_match:
            continue

        # Ano real do raster.
        if product_year is not None:
            try:
                if int(product_year) != year:
                    continue
            except (TypeError, ValueError):
                pass

        # População total.
        if "population" not in combined_text:
            continue

        # Excluir densidade e idade/sexo.
        if "density" in combined_text:
            continue

        if "age" in combined_text:
            continue

        if "sex" in combined_text:
            continue

        raster_url = None

        for asset in assets.values():
            href = asset.get("href")

            if not href:
                continue

            href_lower = href.lower()

            if ".tif" not in href_lower:
                continue

            # Queremos o raster 100m.
            if (
                "100m" not in href_lower
                and "3arc" not in href_lower
            ):
                continue

            raster_url = href
            break

        if not raster_url:
            continue

        candidates.append({
            "dataset_id":
                feature.get("id"),

            "year":
                product_year or year,

            "iso3":
                iso3,

            "country":
                properties.get("name"),

            "raster_url":
                raster_url,

            "properties":
                properties,
        })

    if not candidates:
        return None

    # Preferir constrained.
    candidates.sort(
        key=lambda item:
            0
            if "_CN_" in str(
                item["dataset_id"]
            ).upper()
            else 1
    )

    return candidates[0]
