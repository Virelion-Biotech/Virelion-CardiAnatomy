# Volumetric mesh input preflight

This is a gate between prepared cardiac views and a downstream ventricular volumetric mesher. It is a preflight, not a segmentation or meshing implementation.

## Run

Install optional I/O dependencies with `python -m pip install -e ".[io]"`, then run:

```bash
cardianatomy-volume-mesh-preflight \
  --sax /data/case/SAX.nii.gz \
  --lax-2ch /data/case/LAX_2CH.nii.gz \
  --lax-3ch /data/case/LAX_3CH.nii.gz \
  --lax-4ch /data/case/LAX_4CH.nii.gz \
  --output-manifest /data/results/volume-mesh-preflight.json
```

Checks NIfTI readability, affine finiteness/non-singularity, positive spacing, total voxel safety bound, axis-code convention, and SHA-256 hashes. Manifest avoids absolute paths and DICOM identifiers and will not overwrite an existing file.

## Limitations

- Matching axis codes do not prove that views are registered.
- This command does not segment, infer missing views, invoke a meshing backend, create a tetrahedral mesh, or certify anatomy.
- Tests use synthetic NIfTI images; no patient scan has been run end-to-end.
- Before backend integration, confirm its current input contract, license and model/data terms. Independently validate chamber labels, tissue boundaries, topology, element quality and mesh-to-image registration.
