# Security policy

## Reporting

Report vulnerabilities privately via GitHub's "Report a vulnerability"
(Security tab) on this repository rather than a public issue.

## Scope notes for this project

- **The C runtime parses `.uib` files.** `ps2ui_load` validates every
  offset, count, cross-reference and string terminator before the
  render loop trusts anything, rejects unknown versions, and refuses a
  misaligned blob or table (`PS2UI_ERR_ALIGN`). A libFuzzer harness
  runs over the loader on every change and nightly (S2). Treat blobs
  from strangers as untrusted input anyway.
- **The build tools run on your machine.** `ps2ui-layout` and
  `ps2ui-bake` read HTML/CSS/IR you point them at. Both refuse a
  canvas, element count, nesting depth or source image past a hard cap
  (S3), but neither caps memory or time directly, so don't build
  themes you wouldn't open in an editor.
- **CI runs no untrusted code with write access.** Workflows are
  read-only by default (`permissions: contents: read`); three jobs
  widen it for one purpose each (attaching release files, deploying
  Pages, replacing the fuzz corpus cache). All run on GitHub-hosted
  runners only, and first-time contributors' workflow runs require
  maintainer approval. Please never attach a self-hosted runner to
  this repository.
