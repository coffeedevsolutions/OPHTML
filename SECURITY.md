# Security policy

## Reporting

Report vulnerabilities privately via GitHub's "Report a vulnerability"
(Security tab) on this repository rather than a public issue.

## Scope notes for this project

- **The C runtime parses `.uib` files.** `ps2ui_load` validates every
  offset, count, cross-reference and string terminator before the
  render loop trusts anything, and rejects unknown versions. Treat
  blobs from strangers as untrusted input anyway; a fuzz harness is
  planned (backlog S2).
- **The build tools run on your machine.** `ps2ui-layout` and
  `ps2ui-bake` read HTML/CSS/IR you point them at. Resource-exhaustion
  caps for hostile inputs are planned (backlog S3); until then, don't
  build themes you wouldn't open in an editor.
- **CI runs no untrusted code with write access.** Workflows are
  read-only (`permissions: contents: read`), run on GitHub-hosted
  runners only, and first-time contributors' workflow runs require
  maintainer approval. Please never attach a self-hosted runner to
  this repository.
