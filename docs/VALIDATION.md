# Reference validation metrics

CardiAnatomy 0.4.0 includes lightweight metrics for comparing an anatomy result with an explicitly supplied reference. These functions compute numbers; they do not establish that the reference itself is valid, unbiased, independent, or representative.

## Segmentation overlap

`segmentation_overlap_metrics` compares discrete label arrays with identical shape and reports per-label:

- Dice coefficient;
- Jaccard coefficient;
- intersection voxel count;
- reference voxel count;
- prediction voxel count;
- voxel-count bias.

Background is excluded by default and can be included explicitly.

Recommended use:

- compare a segmentation backend against an independently curated reference mask;
- stratify metrics by chamber/structure instead of reporting only a whole-heart score;
- keep subject-level metrics so failures are not hidden by pooled means.

Do not interpret Dice alone as anatomical truth. Thin structures, topology, boundary placement, and clinically important local errors can remain poor even when volume overlap is high.

## Point-set distance

`point_set_distance_summary` computes bidirectional nearest-point distances between two point sets in the supplied coordinate units. It reports:

- reference→prediction mean distance;
- prediction→reference mean distance;
- symmetric mean;
- symmetric RMS;
- HD95 as the maximum of the two directional 95th percentiles;
- Hausdorff distance.

The implementation is blockwise NumPy so the base package does not require SciPy and does not allocate the full pairwise distance matrix at once.

These are **point-set** metrics. They are not point-to-triangle surface distance unless the supplied points densely sample the actual surfaces. For publication-grade surface evaluation, preserve the exact metric definition used by the benchmark and do not mix Chamfer, point-to-face, ASSD, HD95, and vertex-correspondence error as though they were interchangeable.

## Correspondence vs validation

Dense-correspondence metrics and reference-distance metrics answer different questions:

- `anatomy.correspondence.compare` assumes point index (i) refers to the same anatomical/template point and measures displacement under that correspondence.
- `anatomy.validation.points` ignores point identity and finds nearest points in both directions.

A template-deformation model may have excellent correspondence but inaccurate anatomy; a remeshed surface may have accurate geometry but no meaningful vertex-index correspondence. CardiAnatomy keeps those concepts separate.

## HeartTwin

HeartTwin exposes:

- `anatomy.validation.segmentation`
- `anatomy.validation.points`

Use CardiBench to define the locked cohort/reference policy and CardiEval for independent benchmark reporting when the goal is a scientific performance claim.

## Still required for serious validation

A real validation study should additionally define:

- reference annotation protocol and inter-/intra-observer variability;
- cohort inclusion/exclusion and disease distribution;
- scanner/vendor/protocol distribution;
- preprocessing and registration policy;
- subject-level confidence intervals;
- failure/abstention policy;
- topology/self-intersection metrics where applicable;
- downstream mesh-convergence or simulation-sensitivity analyses;
- external-site validation.

Software tests verify implementation behavior only.
