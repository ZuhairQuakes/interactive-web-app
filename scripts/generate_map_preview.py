#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate the README map preview from Natural Earth and USGS GeoJSON."""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

WORLD_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)
USGS_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson"
)
WIDTH, HEIGHT = 1200, 630
MAP_LEFT, MAP_TOP, MAP_WIDTH, MAP_HEIGHT = 18, 64, 1164, 500


def load_json(source: str) -> dict[str, Any]:
    if source.startswith(("https://", "http://")):
        request = urllib.request.Request(source, headers={"User-Agent": "QuakeImagery-preview/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def project(longitude: float, latitude: float) -> tuple[float, float]:
    x = MAP_LEFT + ((longitude + 180) / 360) * MAP_WIDTH
    y = MAP_TOP + ((90 - latitude) / 180) * MAP_HEIGHT
    return x, y


def polygon_path(ring: list[list[float]]) -> str:
    points = [project(point[0], point[1]) for point in ring]
    if not points:
        return ""
    commands = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    commands.extend(f"L{x:.1f},{y:.1f}" for x, y in points[1:])
    commands.append("Z")
    return "".join(commands)


def country_paths(world: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for feature in world.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates]
        for polygon in polygons:
            for ring in polygon:
                path = polygon_path(ring)
                if path:
                    paths.append(path)
    return paths


def event_details(feature: dict[str, Any]) -> dict[str, Any] | None:
    properties = feature.get("properties") or {}
    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    try:
        magnitude = float(properties["mag"])
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        event_time = datetime.fromtimestamp(float(properties["time"]) / 1000, tz=timezone.utc)
    except (KeyError, TypeError, ValueError, IndexError, OSError):
        return None
    x, y = project(longitude, latitude)
    return {
        "magnitude": magnitude,
        "date": event_time.strftime("%Y-%m-%d"),
        "place": properties.get("place") or "Unnamed event",
        "x": x,
        "y": y,
    }


def choose_annotations(events: list[dict[str, Any]], count: int = 8) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: item["magnitude"], reverse=True):
        if any(math.dist((event["x"], event["y"]), (other["x"], other["y"])) < 72 for other in chosen):
            continue
        chosen.append(event)
        if len(chosen) == count:
            break
    return chosen


def label_position(event: dict[str, Any], occupied: list[tuple[float, float, float, float]]) -> tuple[float, float]:
    width, height = 130, 38
    candidates = [(16, -50), (16, 16), (-146, -50), (-146, 16), (-65, -66)]
    blocked = [(35, 26, 735, 172), (850, 530, 1165, 605)]
    for dx, dy in candidates:
        x = max(8, min(WIDTH - width - 8, event["x"] + dx))
        y = max(8, min(HEIGHT - height - 8, event["y"] + dy))
        box = (x, y, x + width, y + height)
        if not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in blocked + occupied):
            occupied.append(box)
            return x, y
    x = max(8, min(WIDTH - width - 8, event["x"] + 12))
    y = max(8, min(HEIGHT - height - 8, event["y"] + 12))
    occupied.append((x, y, x + width, y + height))
    return x, y


def marker_colour(magnitude: float) -> str:
    if magnitude >= 6:
        return "#fb7185"
    if magnitude >= 5:
        return "#fbbf24"
    return "#38bdf8"


def render(world: dict[str, Any], feed: dict[str, Any]) -> str:
    paths = country_paths(world)
    events = [details for feature in feed.get("features", []) if (details := event_details(feature))]
    annotations = choose_annotations(events)
    occupied: list[tuple[float, float, float, float]] = []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    country_markup = "\n".join(f'      <path d="{path}"/>' for path in paths)
    point_markup = "\n".join(
        f'      <circle cx="{event["x"]:.1f}" cy="{event["y"]:.1f}" r="{max(1.4, min(4.2, event["magnitude"] - 2.8)):.1f}" fill="{marker_colour(event["magnitude"])}"><title>{escape(event["place"])} · M{event["magnitude"]:.1f} · {event["date"]}</title></circle>'
        for event in events
    )
    annotation_markup: list[str] = []
    for event in annotations:
        label_x, label_y = label_position(event, occupied)
        anchor_x = label_x if label_x > event["x"] else label_x + 130
        anchor_y = label_y + 19
        colour = marker_colour(event["magnitude"])
        annotation_markup.append(
            f'''      <g class="annotation">
        <path d="M{event["x"]:.1f},{event["y"]:.1f} L{anchor_x:.1f},{anchor_y:.1f}"/>
        <circle cx="{event["x"]:.1f}" cy="{event["y"]:.1f}" r="8" fill="{colour}"/>
        <rect x="{label_x:.1f}" y="{label_y:.1f}" width="130" height="38" rx="8"/>
        <text x="{label_x + 10:.1f}" y="{label_y + 16:.1f}" class="magnitude">M{event["magnitude"]:.1f}</text>
        <text x="{label_x + 10:.1f}" y="{label_y + 30:.1f}" class="date">{event["date"]}</text>
        <title>{escape(event["place"])} · M{event["magnitude"]:.1f} · {event["date"]}</title>
      </g>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">
  <title id="title">QuakeImagery live earthquake map</title>
  <desc id="description">An accurate Natural Earth world map showing current USGS earthquakes, with the strongest events annotated by magnitude and UTC date.</desc>
  <defs>
    <linearGradient id="ocean" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#071625"/><stop offset="1" stop-color="#123653"/></linearGradient>
    <linearGradient id="land" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#52677a"/><stop offset="1" stop-color="#263b4d"/></linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="8" stdDeviation="11" flood-color="#000" flood-opacity=".38"/></filter>
    <clipPath id="frame"><rect width="1200" height="630" rx="28"/></clipPath>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="1200" height="630" fill="url(#ocean)"/>
    <g fill="none" stroke="#b8d4e8" stroke-opacity=".14" stroke-width="1">
      <path d="M18 189H1182M18 314H1182M18 439H1182"/>
      <path d="M212 64V564M406 64V564M600 64V564M794 64V564M988 64V564"/>
    </g>
    <g fill="url(#land)" stroke="#a8bed0" stroke-opacity=".55" stroke-width=".7" fill-rule="evenodd">
{country_markup}
    </g>
    <g opacity=".72">
{point_markup}
    </g>
    <g class="annotations" font-family="Inter, Arial, sans-serif">
{chr(10).join(annotation_markup)}
    </g>
    <g filter="url(#shadow)">
      <rect x="35" y="26" width="700" height="146" rx="20" fill="#091321" fill-opacity=".95" stroke="#94a3b8" stroke-opacity=".3"/>
      <text x="65" y="65" fill="#38bdf8" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="2">QUAKEIMAGERY · LIVE USGS DATA</text>
      <text x="65" y="111" fill="#f8fafc" font-family="Inter, Arial, sans-serif" font-size="36" font-weight="700">Explore recent earthquakes</text>
      <text x="65" y="146" fill="#b8c6d8" font-family="Inter, Arial, sans-serif" font-size="20">Accurate geography · magnitude and UTC date labels</text>
    </g>
    <g filter="url(#shadow)">
      <rect x="850" y="530" width="315" height="60" rx="30" fill="#0ea5e9"/>
      <text x="1007.5" y="568" fill="#fff" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="21" font-weight="700">Open interactive map →</text>
    </g>
    <text x="35" y="608" fill="#c7d5e2" opacity=".82" font-family="Inter, Arial, sans-serif" font-size="11">Natural Earth basemap · USGS M4.5+ events · generated {generated}</text>
  </g>
  <style>
    .annotation path {{ stroke:#dce8f2; stroke-opacity:.75; stroke-width:1.2; fill:none }}
    .annotation circle {{ stroke:#fff; stroke-width:2.5 }}
    .annotation rect {{ fill:#07111f; fill-opacity:.94; stroke:#b7c8d8; stroke-opacity:.55 }}
    .annotation .magnitude {{ fill:#f8fafc; font-size:13px; font-weight:700 }}
    .annotation .date {{ fill:#bac8d6; font-size:11px }}
  </style>
</svg>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default=WORLD_URL, help="Natural Earth GeoJSON URL or path")
    parser.add_argument("--events", default=USGS_URL, help="USGS GeoJSON URL or path")
    parser.add_argument("--output", type=Path, default=Path("docs/map-preview.svg"))
    args = parser.parse_args()
    args.output.write_text(render(load_json(args.world), load_json(args.events)), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
