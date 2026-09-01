"""Core services for the QuakeImagery application."""

from quakeimagery.usgs import BoundingBox, EarthquakeQuery, fetch_earthquakes

__version__ = "0.1.0"

__all__ = ["BoundingBox", "EarthquakeQuery", "__version__", "fetch_earthquakes"]
