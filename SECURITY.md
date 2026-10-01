# Security and sensitive-data policy

CardiAnatomy may operate near clinical imaging data. The core library is designed not to expose direct DICOM patient identifiers in its inspection API.

## Patient data

- Do not commit patient DICOMs, NIfTI volumes, screenshots, logs, or meshes derived from identifiable clinical data.
- The DICOM inspector omits direct patient identifiers and hashes SeriesInstanceUID values.
- Artifact URIs can reveal sensitive local paths; production deployments should use controlled artifact stores.
- Operators remain responsible for de-identification, access control, encryption, retention, and regulatory obligations.

## External execution

External tool execution uses argument arrays with `shell=False`. Do not replace this with interpolated shell commands. Validate paths and arguments at adapter boundaries and isolate third-party imaging/meshing tools in controlled environments.

## Supply chain

Model weights, atlases, binaries, containers, and other external assets should be hash-pinned and recorded in a `ToolchainManifest`. Unknown or restricted-license tools are disabled by policy unless explicitly reviewed.

## Vulnerabilities

Use GitHub private vulnerability reporting where available. Do not open a public issue containing credentials, patient information, private infrastructure details, or exploitable security information.
