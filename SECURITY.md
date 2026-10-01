# Security and sensitive data

CardiAnatomy may operate near clinical imaging data. The core library is designed not to expose direct DICOM patient identifiers in its inspection API.

Do not commit patient DICOMs, NIfTI volumes, meshes derived from identifiable clinical data, credentials, private model registries, or signed URLs to this repository.

External tool execution uses argument arrays rather than shell interpolation. Deployments should still isolate third-party imaging/meshing tools in controlled environments and review model/data provenance.
