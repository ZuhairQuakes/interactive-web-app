"""Streamlit entry point for QuakeImagery."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from quakeimagery.imagery import ImageryError, load_geotiff_overlay
from quakeimagery.mapping import add_raster_overlay, create_interactive_map
from quakeimagery.usgs import BoundingBox, EarthquakeQuery, USGSQueryError, fetch_earthquakes

st.set_page_config(page_title="QuakeImagery", page_icon="🌎", layout="wide")

AUSTRALIA_BOUNDS = BoundingBox(
    min_latitude=-44.0,
    max_latitude=-10.0,
    min_longitude=112.0,
    max_longitude=154.0,
)


@st.cache_data(ttl=900, show_spinner=False)
def cached_fetch(query: EarthquakeQuery) -> pd.DataFrame:
    """Cache identical USGS requests for 15 minutes."""
    return fetch_earthquakes(query)


def query_form() -> tuple[bool, EarthquakeQuery | None]:
    """Render the sidebar query controls."""
    today = date.today()
    with st.sidebar.form("earthquake-query"):
        st.header("Earthquake query")
        start_date = st.date_input("Start date", today - timedelta(days=30))
        end_date = st.date_input("End date", today)
        min_magnitude = st.number_input(
            "Minimum magnitude",
            min_value=-2.0,
            max_value=10.0,
            value=5.0,
            step=0.1,
        )
        maximum_events = st.number_input(
            "Maximum events",
            min_value=1,
            max_value=20_000,
            value=5_000,
            step=100,
            help="The USGS service rejects queries above 20,000 events.",
        )
        scope = st.selectbox("Geographic scope", ("Worldwide", "Australia", "Custom"))

        bounds = None
        bounds_error = None
        if scope == "Australia":
            bounds = AUSTRALIA_BOUNDS
        elif scope == "Custom":
            min_latitude = st.number_input("Minimum latitude", -90.0, 90.0, -45.0)
            max_latitude = st.number_input("Maximum latitude", -90.0, 90.0, 45.0)
            min_longitude = st.number_input("Minimum longitude", -360.0, 360.0, -180.0)
            max_longitude = st.number_input("Maximum longitude", -360.0, 360.0, 180.0)
            try:
                bounds = BoundingBox(
                    min_latitude=min_latitude,
                    max_latitude=max_latitude,
                    min_longitude=min_longitude,
                    max_longitude=max_longitude,
                )
            except ValueError as exc:
                bounds_error = str(exc)
                st.warning(bounds_error)

        submitted = st.form_submit_button("Fetch earthquakes", type="primary")

    if not submitted:
        return False, None
    if bounds_error is not None:
        st.sidebar.error(bounds_error)
        return True, None

    try:
        query = EarthquakeQuery(
            start_date=start_date,
            end_date=end_date,
            min_magnitude=float(min_magnitude),
            maximum_events=int(maximum_events),
            bounds=bounds,
        )
    except ValueError as exc:
        st.sidebar.error(str(exc))
        return True, None
    return True, query


def main() -> None:
    st.title("QuakeImagery")
    st.caption("Explore USGS earthquake events with an optional georeferenced raster overlay.")

    submitted, query = query_form()
    if submitted and query is not None:
        try:
            with st.spinner("Querying the USGS Earthquake Catalog…"):
                st.session_state["earthquakes"] = cached_fetch(query)
                st.session_state["last_query"] = query
        except USGSQueryError as exc:
            st.error(str(exc))

    earthquakes = st.session_state.get("earthquakes")
    if earthquakes is None:
        st.info("Choose a date range and geographic scope, then fetch earthquake data.")
        return

    if earthquakes.empty:
        st.warning("The query returned no earthquake events.")
        return

    st.subheader(f"{len(earthquakes):,} earthquake events")
    last_query = st.session_state.get("last_query")
    if last_query is not None and len(earthquakes) >= last_query.maximum_events:
        st.warning(
            "The result reached the selected event limit. Narrow the dates, magnitude, "
            "or geographic bounds for a complete result set."
        )
    st.dataframe(
        earthquakes[
            ["time", "magnitude", "place", "latitude", "longitude", "depth_km", "url"]
        ],
        hide_index=True,
        width="stretch",
        column_config={"url": st.column_config.LinkColumn("USGS event")},
    )

    uploaded_raster = st.file_uploader(
        "Optional imagery overlay",
        type=("tif", "tiff"),
        help="Upload a georeferenced EPSG:4326 GeoTIFF. Files are processed in memory.",
    )

    map_object = create_interactive_map(earthquakes)
    if uploaded_raster is not None:
        try:
            overlay = load_geotiff_overlay(uploaded_raster.getvalue())
            add_raster_overlay(map_object, overlay)
        except ImageryError as exc:
            st.error(f"Could not use the GeoTIFF: {exc}")

    st_folium(map_object, width=1200, height=650, returned_objects=())
    map_html = map_object.get_root().render()
    st.download_button(
        "Download map as HTML",
        data=map_html,
        file_name="quakeimagery-map.html",
        mime="text/html",
    )

    st.caption(
        "Earthquake data are provided by the USGS Earthquake Catalog. "
        "This exploratory tool is not an official hazard assessment."
    )


if __name__ == "__main__":
    main()
