import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds

from quakeimagery.imagery import ImageryError, load_geotiff_overlay


def geotiff_bytes(*, crs="EPSG:4326"):
    profile = {
        "driver": "GTiff",
        "height": 2,
        "width": 3,
        "count": 1,
        "dtype": "uint8",
        "crs": crs,
        "transform": from_bounds(100, -10, 103, -8, 3, 2),
    }
    with MemoryFile() as memory_file:
        with memory_file.open(**profile) as dataset:
            dataset.write(np.array([[0, 50, 100], [150, 200, 250]], dtype="uint8"), 1)
        return memory_file.read()


def test_geotiff_is_normalized_to_rgba():
    overlay = load_geotiff_overlay(geotiff_bytes())

    assert overlay.image.shape == (2, 3, 4)
    assert overlay.image.min() >= 0
    assert overlay.image.max() <= 1
    assert overlay.bounds == [[-10.0, 100.0], [-8.0, 103.0]]


def test_non_wgs84_geotiff_is_rejected():
    with pytest.raises(ImageryError, match="EPSG:4326"):
        load_geotiff_overlay(geotiff_bytes(crs="EPSG:3857"))
