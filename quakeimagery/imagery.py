"""Read small, georeferenced GeoTIFFs for browser map overlays."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
from rasterio.enums import Resampling
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_DISPLAY_PIXELS = 2_000_000


class ImageryError(ValueError):
    """Raised when an uploaded raster cannot be displayed safely."""


@dataclass(frozen=True)
class RasterOverlay:
    """Normalized in-memory raster and its WGS84 map bounds."""

    image: np.ndarray
    bounds: list[list[float]]


def _normalize_band(band: np.ma.MaskedArray, valid: np.ndarray) -> np.ndarray:
    values = band.astype("float64").filled(np.nan)
    finite = valid & np.isfinite(values)
    if not finite.any():
        return np.zeros(values.shape, dtype="float64")
    low, high = np.nanpercentile(values[finite], (2, 98))
    if high <= low:
        low, high = np.nanmin(values[finite]), np.nanmax(values[finite])
    if high <= low:
        return np.zeros(values.shape, dtype="float64")
    normalized = np.clip((values - low) / (high - low), 0, 1)
    normalized[~finite] = 0
    return normalized


def load_geotiff_overlay(content: bytes) -> RasterOverlay:
    """Load an EPSG:4326 GeoTIFF and return a browser-sized RGBA overlay."""
    if not content:
        raise ImageryError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ImageryError("The GeoTIFF is larger than the 50 MB upload limit.")

    try:
        with MemoryFile(content) as memory_file, memory_file.open() as source:
            if source.crs is None:
                raise ImageryError("The GeoTIFF has no coordinate reference system.")
            if source.crs.to_epsg() != 4326:
                raise ImageryError("The GeoTIFF must use EPSG:4326 geographic coordinates.")
            if source.count < 1:
                raise ImageryError("The GeoTIFF contains no raster bands.")

            scale = min(1.0, sqrt(MAX_DISPLAY_PIXELS / (source.width * source.height)))
            height = max(1, round(source.height * scale))
            width = max(1, round(source.width * scale))
            indexes = list(range(1, min(source.count, 3) + 1))
            bands = source.read(
                indexes,
                out_shape=(len(indexes), height, width),
                resampling=Resampling.bilinear,
                masked=True,
            )
            mask = np.ma.getmaskarray(bands)
            valid = ~np.any(mask, axis=0)
            normalized = [_normalize_band(band, valid) for band in bands]
            if len(normalized) == 1:
                normalized *= 3
            elif len(normalized) == 2:
                normalized.append(normalized[0])
            alpha = valid.astype("float64")
            image = np.dstack((*normalized[:3], alpha))
            bounds = [
                [source.bounds.bottom, source.bounds.left],
                [source.bounds.top, source.bounds.right],
            ]
    except ImageryError:
        raise
    except (RasterioError, OSError, ValueError) as exc:
        raise ImageryError(f"Rasterio could not read the upload: {exc}") from exc

    return RasterOverlay(image=image, bounds=bounds)
