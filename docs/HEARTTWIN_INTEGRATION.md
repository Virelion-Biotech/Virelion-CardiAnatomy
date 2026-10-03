# HeartTwin integration

CardiAnatomy is a native HeartTwin service and the upstream geometry authority for anatomy-aware downstream components.

## Capabilities

- `anatomy.health`
- `anatomy.build`
- `anatomy.validate`
- `anatomy.tools`
- `anatomy.microstructure.reference`
- `anatomy.scar.classify`
- `anatomy.presets`
- `anatomy.registration.rigid`
- `anatomy.geometry.measure`
- `anatomy.manifest.audit`
- `anatomy.series.rank`
- `anatomy.segmentation.qc`
- `anatomy.cine.phases`
- `anatomy.transforms.compose`
- `anatomy.transforms.invert`
- `anatomy.correspondence.compare`
- `anatomy.motion.summarize`
- `anatomy.validation.segmentation`
- `anatomy.validation.points`

HeartTwin's packaged registry advertises the same capability set and dispatches it in-process when the pinned CardiAnatomy package is installed.

## State boundary

HeartTwin should persist a compact typed anatomy artifact containing:

- subject/study/acquisition identity;
- artifact references and hashes;
- coordinate frames and registrations;
- stage/provenance records;
- numerical QC;
- readiness state;
- bundle fingerprint.

Large VTK/VTU/NIfTI/DICOM/HDF5 assets remain outside the orchestration state.

Correspondence and motion results should carry the originating geometry/bundle fingerprint so downstream calibration cannot silently mix incompatible meshes.

## Downstream gates

- CardiEP: require `ep` readiness before patient-specific geometry/fiber execution.
- CardiMech: require `mechanics` readiness.
- CardiFlow: require `flow` readiness.
- CardiInfer: consume geometry, registration, and correspondence uncertainty as inference context.
- ElectroTrace calibration: anatomy-dependent calibration should reference the exact anatomy bundle/frame used to construct the EP observation model.

No downstream component should infer coordinate frames, phase identity, correspondence, or topology from filenames or directory conventions.

## Clean-stack verification

HeartTwin's full integration workflow installs a pinned CardiAnatomy Git revision from `requirements-services.txt`, requires the native service to be available, smoke-tests anatomy capabilities, and then runs the complete HeartTwin suite across Python 3.10–3.12.

Passing that integration verifies software compatibility only; it does not validate patient-specific anatomy.
