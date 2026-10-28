# CardiAnatomy 3D Viewer

This static browser tool is for **surface mesh inspection**. It visualizes supplied geometry but does not segment scans, infer anatomy, repair topology, or certify clinical validity.

## Open it

Once the viewer-pages GitHub Actions workflow has deployed the viewer directory, open the Pages URL from that workflow. For local development, serve the repository root with a static HTTP server, for example:

    python -m http.server 8000

Then visit http://localhost:8000/viewer/. Serving over HTTP is recommended instead of opening the HTML through a file URL because browser module/CORS rules differ.

The first view is a synthetic teaching illustration, not patient-derived anatomy or an anatomically validated reference.

## File formats

- .vtk: legacy ASCII POLYDATA surface with polygons that can be triangulated.
- .stl: ASCII or binary triangle surface.
- .obj: OBJ surface geometry; companion MTL/texture files are not loaded by the single-file upload.
- .ply: PLY surface geometry, including vertex colors when present.
- .glb: self-contained GL Transmission Format binary model. Separate glTF files with external assets are not supported by the single-file upload.

The viewer does not directly open volume-mesh VTK UNSTRUCTURED_GRID, .vtu, image volumes, DICOM folders, NIfTI, or segmentation masks. It needs an exterior polygon surface, not a finite-element volume or source scan.

## Convert a supported linear volume mesh to a viewable surface

Install the IO dependencies in a local CardiAnatomy checkout:

    python -m pip install -e '.[io]'
    cardianatomy export-surface path/to/volume_mesh.vtu outputs/volume_surface.vtk

Then open outputs/volume_surface.vtk in the viewer. The command supports linear tetra, hexahedron, wedge, and pyramid volume cells, finds faces shared by two cells, and exports the exterior as legacy ASCII VTK POLYDATA. It also accepts a surface mesh composed of linear triangles/quadrilaterals. High-order, voxel and polyhedron cells fail explicitly rather than being silently flattened.

The output is **geometry only**: scalar fields, fiber arrays, scar values, labels, and cell attributes are not preserved. Coordinates are not rescaled or converted to physical units. Check the coordinate frame, unit convention, surface orientation and mesh QC before using the result downstream.

## Controls and privacy

- Drag to rotate; use the wheel or trackpad to zoom; right-drag to pan.
- Fit the model to view, toggle wireframe/axes, and export the viewport to PNG.
- Selected local mesh bytes are parsed in the browser and are not posted to a backend. The page loads pinned Three.js modules from jsDelivr, so an internet connection is required.
- Counts/bounds are geometry bookkeeping, not anatomical measurements. Bounds use the input coordinate units, which may be unknown.

A visible surface, attractive rendering, or passing geometric QC does not establish segmentation accuracy, anatomical truth, clinical validation or regulatory suitability.
