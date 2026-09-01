from __future__ import annotations

from quakeimagery.cli import streamlit_arguments


def test_streamlit_arguments_target_the_installed_application() -> None:
    arguments = streamlit_arguments(["--server.headless=true"])

    assert arguments[:2] == ["streamlit", "run"]
    assert arguments[2].endswith("streamlit_app.py")
    assert arguments[3:] == ["--server.headless=true"]
