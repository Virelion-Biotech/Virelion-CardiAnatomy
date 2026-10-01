# Geometry QC

CardiAnatomy separates **software/geometry QC** from **scientific validation**.

## Implemented numerical checks

For tetrahedral meshes:

- non-empty points/cells;
- finite coordinates and volumes;
- connected-component count;
- degenerate tetrahedron fraction;
- minority orientation fraction (mixed orientation detection);
- edge-length range;
- absolute tetrahedral-volume range.

For triangular surfaces:

- non-empty points/cells;
- finite coordinates/areas;
- connected components;
- degenerate triangle fraction;
- non-manifold edge count;
- boundary edge count;
- optional watertight requirement;
- edge-length range.

## Not yet equivalent to scientific validation

These checks do not measure:

- Dice/Hausdorff segmentation accuracy;
- landmark error;
- chamber volume accuracy;
- scar-label accuracy;
- anatomical plausibility against independent reference imaging;
- mesh convergence for a downstream PDE;
- uncertainty due to registration or segmentation.

Those require benchmark datasets and should eventually be evaluated through CardiBench/CardiEval.
