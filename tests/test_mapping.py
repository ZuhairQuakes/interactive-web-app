import pandas as pd

from quakeimagery.mapping import create_interactive_map


def test_map_contains_normalized_event_details():
    earthquakes = pd.DataFrame(
        [
            {
                "event_id": "example-1",
                "time": "2024-01-01 00:00:00+00:00",
                "updated": "2024-01-01 01:00:00+00:00",
                "magnitude": 6.5,
                "place": "Test Region",
                "latitude": -37.2,
                "longitude": 145.1,
                "depth_km": 12.3,
                "url": "https://example.test/event",
            }
        ]
    )

    html = create_interactive_map(earthquakes).get_root().render()

    assert "Magnitude: 6.5" in html
    assert "Test Region" in html


def test_empty_catalog_still_returns_a_map():
    map_object = create_interactive_map(pd.DataFrame())

    assert map_object.location == [0.0, 0.0]
