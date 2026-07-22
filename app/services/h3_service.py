import h3


def coordinates_to_h3(latitude: float, longitude: float, resolution: int = 9):
    h3_index = h3.latlng_to_cell(
        latitude,
        longitude,
        resolution
    )

    center_latitude, center_longitude = h3.cell_to_latlng(h3_index)

    return {
        "h3_index": h3_index,
        "resolution": resolution,
        "cell_center": {
            "latitude": center_latitude,
            "longitude": center_longitude
        }
    }
