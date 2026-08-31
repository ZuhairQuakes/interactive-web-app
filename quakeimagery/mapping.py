"""Folium map construction for earthquake events and raster overlays."""

from __future__ import annotations

from html import escape

import folium
import pandas as pd
from folium.plugins import Fullscreen, MarkerCluster

from quakeimagery.imagery import RasterOverlay


def _magnitude_color(magnitude: float) -> str:
    if magnitude >= 7:
        return "darkred"
    if magnitude >= 6:
        return "red"
    if magnitude >= 5:
        return "orange"
    return "blue"


def create_interactive_map(earthquakes: pd.DataFrame) -> folium.Map:
    """Create a clustered map and fit it to the supplied earthquake events."""
    if earthquakes.empty:
        return folium.Map(location=(0, 0), zoom_start=2, control_scale=True)

    center = (earthquakes["latitude"].mean(), earthquakes["longitude"].mean())
    map_object = folium.Map(location=center, zoom_start=3, control_scale=True)
    cluster = MarkerCluster(name="Earthquakes").add_to(map_object)

    for event in earthquakes.itertuples(index=False):
        magnitude = float(event.magnitude)
        place = escape(str(event.place))
        popup = (
            f"<strong>{place}</strong><br>"
            f"Magnitude: {magnitude:.1f}<br>"
            f"Depth: {float(event.depth_km):.1f} km<br>"
            f"Time: {escape(str(event.time))}"
        )
        folium.CircleMarker(
            location=(event.latitude, event.longitude),
            radius=max(4, min(14, 3 + magnitude)),
            color=_magnitude_color(magnitude),
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup, max_width=320),
            tooltip=f"M {magnitude:.1f} — {place}",
        ).add_to(cluster)

    locations = earthquakes[["latitude", "longitude"]].dropna().values.tolist()
    if len(locations) > 1:
        map_object.fit_bounds(locations, padding=(20, 20))
    Fullscreen(position="topright").add_to(map_object)
    folium.LayerControl(collapsed=False).add_to(map_object)
    return map_object


def add_raster_overlay(map_object: folium.Map, overlay: RasterOverlay) -> None:
    """Add a normalized raster overlay to an existing map."""
    folium.raster_layers.ImageOverlay(
        image=overlay.image,
        bounds=overlay.bounds,
        name="Uploaded imagery",
        opacity=0.65,
        origin="upper",
        mercator_project=True,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(map_object)
