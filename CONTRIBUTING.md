# Contributing to Virelion CardiAnatomy

CardiAnatomy sits on a scientific boundary where apparently harmless defaults can become implicit biological claims. Contributions should optimize for explicit contracts, reproducibility, and fail-closed behavior.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests scripts
pytest -q
python scripts/generate_schemas.py --check
```

## Scientific rules

- Do not invent missing anatomical metadata, landmarks, coordinate frames, or acquisition identity.
- New backends must declare upstream software, model, data versions, and licenses.
- Patient-derived artifacts must retain caller-supplied subject/study/acquisition identity without logging direct PHI.
- Distinguish patient-derived, template-derived, and synthetic geometry in provenance.
- A software test cannot promote a backend to empirical or clinical validation.
- New coordinate transformations require tests with known points.
- New mesh transformations require pre/post QC.
- Keep GPU segmentation, meshing toolchains, FEniCS, and solver runtimes optional.
- Model weights and datasets require provenance and license records independent of the software license.
- External tools must be added to the license-aware integration catalog.

## Public-contract changes

A change to a versioned Pydantic contract should include:
1. tests for the new invariant;
2. schema regeneration where applicable;
3. migration notes if compatibility changes;
4. updates to HeartTwin integration documentation when capabilities change.

Prefer small domain modules and explicit stage backends over monolithic workflow scripts.
