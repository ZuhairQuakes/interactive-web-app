from datetime import date

import pandas as pd
import pytest

from quakeimagery.usgs import BoundingBox, EarthquakeQuery, USGSQueryError, fetch_earthquakes


class FakeResponse:
    def __init__(self, payload, *, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.request = None

    def get(self, url, *, params, timeout):
        self.request = {"url": url, "params": params, "timeout": timeout}
        return self.response


def sample_payload():
    return {
        "features": [
            {
                "id": "example-1",
                "properties": {
                    "mag": 6.2,
                    "place": "Test Region",
                    "time": 1_700_000_000_000,
                    "updated": 1_700_000_100_000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/example-1",
                },
                "geometry": {"coordinates": [145.1, -37.2, 12.3]},
            }
        ]
    }


def test_query_builds_documented_usgs_parameters():
    query = EarthquakeQuery(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        min_magnitude=5.5,
        maximum_events=250,
        bounds=BoundingBox(-45, -10, 112, 154),
    )

    parameters = query.as_parameters()

    assert parameters["format"] == "geojson"
    assert parameters["eventtype"] == "earthquake"
    assert parameters["limit"] == 250
    assert parameters["minlatitude"] == -45
    assert parameters["endtime"].startswith("2024-01-02T23:59:59")


def test_fetch_normalizes_geojson_features():
    session = FakeSession(FakeResponse(sample_payload()))
    query = EarthquakeQuery(date(2024, 1, 1), date(2024, 1, 2))

    result = fetch_earthquakes(query, session=session, timeout=5)

    assert len(result) == 1
    assert result.loc[0, "event_id"] == "example-1"
    assert result.loc[0, "latitude"] == -37.2
    assert result.loc[0, "depth_km"] == 12.3
    assert isinstance(result.loc[0, "time"], pd.Timestamp)
    assert session.request["timeout"] == 5


def test_invalid_date_range_is_rejected():
    with pytest.raises(ValueError, match="End date"):
        EarthquakeQuery(date(2024, 1, 2), date(2024, 1, 1))


def test_unexpected_response_is_reported():
    session = FakeSession(FakeResponse({"metadata": {}}))
    query = EarthquakeQuery(date(2024, 1, 1), date(2024, 1, 2))

    with pytest.raises(USGSQueryError, match="feature list"):
        fetch_earthquakes(query, session=session)


def test_incomplete_event_is_ignored():
    payload = sample_payload()
    payload["features"].append(
        {"id": "incomplete", "properties": {"mag": None}, "geometry": {"coordinates": []}}
    )
    session = FakeSession(FakeResponse(payload))
    query = EarthquakeQuery(date(2024, 1, 1), date(2024, 1, 2))

    result = fetch_earthquakes(query, session=session)

    assert result["event_id"].tolist() == ["example-1"]
