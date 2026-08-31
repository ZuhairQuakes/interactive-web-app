"""Typed client helpers for the USGS FDSN Event Web Service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any

import pandas as pd
import requests

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
EVENT_COLUMNS = (
    "event_id",
    "time",
    "updated",
    "magnitude",
    "place",
    "latitude",
    "longitude",
    "depth_km",
    "url",
)


class USGSQueryError(RuntimeError):
    """Raised when the USGS service cannot return a valid catalog response."""


@dataclass(frozen=True)
class BoundingBox:
    """Rectangular query bounds in decimal degrees."""

    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.min_latitude < self.max_latitude <= 90:
            raise ValueError("Latitude bounds must increase within -90 to 90 degrees.")
        if not -360 <= self.min_longitude < self.max_longitude <= 360:
            raise ValueError("Longitude bounds must increase within -360 to 360 degrees.")

    def as_parameters(self) -> dict[str, float]:
        return {
            "minlatitude": self.min_latitude,
            "maxlatitude": self.max_latitude,
            "minlongitude": self.min_longitude,
            "maxlongitude": self.max_longitude,
        }


@dataclass(frozen=True)
class EarthquakeQuery:
    """Validated inputs for an earthquake catalog query."""

    start_date: date
    end_date: date
    min_magnitude: float = 5.0
    maximum_events: int = 5_000
    bounds: BoundingBox | None = None

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date.")
        if not -10 <= self.min_magnitude <= 10:
            raise ValueError("Minimum magnitude must be between -10 and 10.")
        if not 1 <= self.maximum_events <= 20_000:
            raise ValueError("Maximum events must be between 1 and 20,000.")

    def as_parameters(self) -> dict[str, Any]:
        start = datetime.combine(self.start_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(self.end_date, time.max, tzinfo=timezone.utc)
        parameters: dict[str, Any] = {
            "format": "geojson",
            "eventtype": "earthquake",
            "starttime": start.isoformat(),
            "endtime": end.isoformat(),
            "minmagnitude": self.min_magnitude,
            "limit": self.maximum_events,
            "orderby": "time",
        }
        if self.bounds is not None:
            parameters.update(self.bounds.as_parameters())
        return parameters


def _feature_to_row(feature: dict[str, Any]) -> dict[str, Any] | None:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 3:
        return None
    return {
        "event_id": feature.get("id"),
        "time": properties.get("time"),
        "updated": properties.get("updated"),
        "magnitude": properties.get("mag"),
        "place": properties.get("place") or "Unknown location",
        "latitude": coordinates[1],
        "longitude": coordinates[0],
        "depth_km": coordinates[2],
        "url": properties.get("url"),
    }


def fetch_earthquakes(
    query: EarthquakeQuery,
    *,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Fetch and normalize earthquake events from the USGS catalog."""
    client = session or requests.Session()
    try:
        response = client.get(USGS_QUERY_URL, params=query.as_parameters(), timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise USGSQueryError(f"USGS earthquake query failed: {exc}") from exc

    features = payload.get("features")
    if not isinstance(features, list):
        raise USGSQueryError("USGS returned an unexpected response without a feature list.")

    rows = [row for feature in features if (row := _feature_to_row(feature)) is not None]
    frame = pd.DataFrame(rows, columns=EVENT_COLUMNS)
    if frame.empty:
        return frame

    for column in ("magnitude", "latitude", "longitude", "depth_km"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["time"] = pd.to_datetime(frame["time"], unit="ms", utc=True, errors="coerce")
    frame["updated"] = pd.to_datetime(frame["updated"], unit="ms", utc=True, errors="coerce")
    return frame.dropna(subset=["magnitude", "latitude", "longitude", "depth_km"]).reset_index(
        drop=True
    )
