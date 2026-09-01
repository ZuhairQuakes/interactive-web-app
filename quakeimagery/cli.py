"""Command-line launcher for the QuakeImagery Streamlit application."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path


def streamlit_arguments(arguments: Sequence[str]) -> list[str]:
    """Build Streamlit arguments without importing the application module."""
    application = importlib.util.find_spec("streamlit_app")
    if application is None or application.origin is None:
        raise RuntimeError("The QuakeImagery application module is not installed.")
    return ["streamlit", "run", str(Path(application.origin)), *arguments]


def main() -> int | None:
    """Launch the installed Streamlit application."""
    from streamlit.web import cli as streamlit_cli

    sys.argv = streamlit_arguments(sys.argv[1:])
    return streamlit_cli.main()
