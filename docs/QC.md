# Geometry and anatomy QC

CardiAnatomy separates **software/numerical QC** from **scientific validation**.

## Implemented tetrahedral-mesh checks

- non-empty points/cells;
- finite coordinates and signed volumes;
- connected-component count;
- degenerate tetrahedron fraction;
- mixed-orientation detection;
- edge-length range;
- absolute tetrahedral-volume range;
- normalized tetrahedral mean-ratio quality;
- normalized minimum-corner scaled-Jacobian quality.

Optional `minimum_shape_quality` can fail a mesh when normalized shape quality drops below an explicit threshold.

## Implemented triangular-surface checks

- non-empty points/cells;
- finite coordinates and areas;
- connected components;
- degenerate triangle fraction;
- non-manifold edge count;
- boundary edge count;
- optional watertight requirement;
- edge-length range;
- normalized triangle shape quality.

## Segmentation and cine checks

The segmentation utilities report present/missing labels, foreground fraction, and spatial label volumes. Volume calculation intentionally accepts one 3D phase at a time so temporal spacing cannot be mistaken for a spatial voxel dimension.

For 4D cine segmentations, CardiAnatomy can compute a chamber-volume curve, select ED/ES from maximum/minimum cavity volume, and report stroke volume, ejection fraction, and dynamic range. Flat/near-flat curves are rejected by an explicit dynamic-range threshold.

## Correspondence and motion checks

For meshes that are claimed to share dense correspondence, CardiAnatomy can compare point counts, exact connectivity, connectivity hashes, displacement distributions, temporal step motion, vertex path length, and cyclic closure.

These checks do **not** prove a deformation is diffeomorphic, free of self-intersection, or anatomically correct.

## What remains scientific validation

Numerical QC does not establish:

- Dice/Hausdorff or surface-distance segmentation accuracy;
- landmark accuracy;
- chamber-volume agreement against an independent reference;
- wall-thickness or strain accuracy;
- scar-label accuracy;
- anatomical plausibility across disease/cohort distributions;
- registration target error on independent landmarks;
- mesh convergence for a downstream PDE;
- EP/mechanics/hemodynamics predictive validity;
- calibrated uncertainty.

Those require external benchmarks and should be evaluated through CardiBench/CardiEval with cohort-appropriate references.
