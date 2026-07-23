from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.h3_coverage_service import (
    geojson_to_h3_coverage,
)


router = APIRouter(
    prefix="/h3",
    tags=["H3 Coverage"],
)


class H3CoverageRequest(BaseModel):
    geometry: dict[str, Any]

    resolution: int = Field(
        default=9,
        ge=0,
        le=15,
    )


@router.post("/coverage")
async def h3_coverage(
    data: H3CoverageRequest
):
    try:
        cells = geojson_to_h3_coverage(
            geometry=data.geometry,
            resolution=data.resolution,
        )

        return {
            "success": True,
            "resolution": data.resolution,
            "cells_count": len(cells),
            "cells": cells,
        }

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
