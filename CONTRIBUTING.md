# Contributing

Thank you for helping improve QuakeImagery.

## Local workflow

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check .
pytest
python tools/validate_repository.py
```

Run the app with `streamlit run streamlit_app.py` after the checks pass.

## Change expectations

- Keep USGS query parameters aligned with the official FDSN Event Web Service.
- Add tests for response parsing, query validation, or raster handling when those behaviours change.
- Use small synthetic in-memory rasters in tests; do not commit downloaded satellite products or generated HTML maps.
- Treat uploaded files and remote API responses as untrusted input. Never commit credentials or Streamlit secrets.
- Document the coordinate reference system, bands, source, acquisition date, and processing history for imagery used in a scientific analysis.

Pull requests should explain user-visible changes and distinguish interface improvements from changes that affect scientific interpretation.
