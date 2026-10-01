# HeartTwin integration

CardiAnatomy should be exposed to HeartTwin as a native package before using HTTP transport.

Initial capabilities:

- `anatomy.health`
- `anatomy.build`
- `anatomy.validate`

HeartTwin should record the returned `AnatomyBundle` as a typed artifact and must not mark a geometry as personalization-ready unless `bundle.ready` is true.

Downstream ownership:

- CardiEP consumes mesh, fibers, scar, coordinates, and EAM/ECG registrations.
- CardiMech consumes meshes, surfaces, microstructure, chamber labels, and pressure/volume registration.
- CardiFlow consumes chamber/vascular geometry plus flow-domain boundary mappings.
- CardiInfer consumes anatomy QC and transformation uncertainty as part of the inference context.

Large artifacts should remain external and be referenced by URI + digest rather than embedded in HeartTwin state.
