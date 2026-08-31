from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

DEMO_PATH = Path(__file__).resolve().parents[1] / "docs" / "index.html"
USGS_FEED = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson"
)


class DemoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.magnitude_filters: set[str] = set()
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.add(element_id)
        if minimum := attributes.get("data-minimum"):
            self.magnitude_filters.add(minimum)
        if tag == "script" and (source := attributes.get("src")):
            self.scripts.append(source)


def test_map_demo_has_required_controls_and_dependencies() -> None:
    html = DEMO_PATH.read_text(encoding="utf-8")
    parser = DemoParser()
    parser.feed(html)

    assert {"map", "map-title", "status", "refresh"} <= parser.ids
    assert parser.magnitude_filters == {"4.5", "5", "6"}
    assert parser.scripts == ["https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"]


def test_map_demo_uses_the_official_usgs_feed_safely() -> None:
    html = DEMO_PATH.read_text(encoding="utf-8")

    assert USGS_FEED in html
    assert 'rel="noopener noreferrer"' in html
    assert "textContent =" in html
    assert "innerHTML" not in html
