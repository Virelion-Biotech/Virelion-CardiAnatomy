# Scientific audit changes — 2026-10-09

## Behavior

Add scar threshold-hypothesis class frequencies and a three-grid scalar solution GCI assessment.

## Scope and remaining evidence

Frequencies measure threshold sensitivity, not calibrated tissue probabilities. GCI requires a constant refinement ratio and monotone asymptotic behavior, and is not a mandatory mesh-generation hook or evidence that the spatial solvers meet the benchmark tolerances. Fibers, reference configuration and patient validation remain unresolved.

## Implementation

- `src/cardianatomy/convergence.py`
- `tests/test_uncertainty_convergence.py`
- `src/cardianatomy/scar.py`

## Verification

Regression tests accompany the changes. Repository test results are recorded in the audit completion report and draft pull request. Software regression checks do not establish numerical, biological, transport or clinical validity.
