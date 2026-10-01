# HeartTwin integration

CardiAnatomy is a native HeartTwin service.

## Capabilities

- `anatomy.health`
- `anatomy.build`
- `anatomy.validate`
- `anatomy.tools`
- `anatomy.microstructure.reference`
- `anatomy.scar.classify`

## Proposed registry entry

```yaml
- name: CardiAnatomy
  repository: Virelion-Biotech/Virelion-CardiAnatomy
  capabilities:
    - anatomy.health
    - anatomy.build
    - anatomy.validate
    - anatomy.tools
    - anatomy.microstructure.reference
    - anatomy.scar.classify
  builtin: cardianatomy
  endpoint: ${CARDIANATOMY_URL}
```

## State boundary

HeartTwin should persist a compact typed anatomy artifact containing the bundle identity, artifact references, frames/registrations, QC, readiness, and bundle fingerprint. Large VTK/NIfTI/DICOM/HDF5 data should remain external.

## Downstream gates

- CardiEP: require `ep` readiness for patient-specific execution.
- CardiMech: require `mechanics` readiness.
- CardiFlow: require `flow` readiness.
- CardiInfer: consume geometry/registration uncertainty and bundle fingerprints as inference context.

No downstream component should infer coordinate frames from filenames or directory conventions.
