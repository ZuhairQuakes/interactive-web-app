# Contributing

Thank you for helping improve QuakeImagery.

## Local workflow

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
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

## Issues and pull requests

Search existing issues before opening a new one and use the supplied issue
templates. Keep pull requests focused, update tests and documentation together,
and add user-visible changes beneath `Unreleased` in `CHANGELOG.md`.

By contributing, you agree that your contribution will be licensed under the
project's [MIT License](LICENSE) and that you will follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Releases

Maintainers use [Semantic Versioning](https://semver.org/). To prepare a release:

1. Move relevant changelog entries from `Unreleased` into a dated version section.
2. Update the version in `pyproject.toml`, `quakeimagery/__init__.py`, and `CITATION.cff`.
3. Run the complete local workflow and merge the release commit into `main`.
4. Create and push an annotated `vX.Y.Z` tag. The release workflow builds the
   source and wheel distributions and attaches them to a GitHub Release.
