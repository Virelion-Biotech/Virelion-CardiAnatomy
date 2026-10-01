# Contributing

## Scientific rules

- Do not invent missing anatomical metadata.
- New backends must declare upstream software/model/data versions and licenses.
- Patient-derived artifacts must retain subject/study/acquisition identity supplied by the caller without logging direct PHI.
- A software test cannot promote a backend to empirical or clinical validation.
- New coordinate transformations require tests with known points.
- New mesh transformations require pre/post QC.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests scripts
pytest -q
python scripts/generate_schemas.py --check
```
