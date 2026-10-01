# CardiAnatomy architecture

## Responsibility boundary

CardiAnatomy is the anatomy and spatial-registration layer of HeartTwin. It defines stable contracts while allowing scientific implementations to evolve behind backend interfaces.

The core package must remain lightweight and deterministic. Heavy imaging dependencies, GPU segmentation stacks, meshing toolchains, and solver-specific exporters belong in optional backend packages or deployment images.

## Canonical flow

```text
ImagingAcquisition
  -> segmentation
  -> surfaces
  -> volumetric mesh
  -> coordinate/microstructure fields
  -> scar and border-zone labels
  -> cross-modality registrations
  -> GeometryQC
  -> AnatomyBundle
```

Every artifact should be addressable, hashable, and linked to a subject/study/acquisition. Cross-modality transforms must state source and target coordinate frames.

## Planned backend families

- CMR/CT segmentation
- biventricular surface fitting
- tetrahedral meshing
- rule-based or data-derived fiber generation
- LGE scar/border-zone mapping
- electrode/EAM registration
- Echo/CMR/CT spatial alignment
- solver-specific export adapters

No backend is considered scientifically validated merely because it satisfies the software contract.
