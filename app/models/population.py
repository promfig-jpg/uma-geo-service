from pydantic import BaseModel, Field


class PopulationPoint(BaseModel):
    h3_index: str

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


class PopulationBatchRequest(BaseModel):
    points: list[PopulationPoint]

    iso3: str = "BRA"

    year: int = 2025
