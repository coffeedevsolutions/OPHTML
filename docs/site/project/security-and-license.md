---
id: project/security-and-license
title: Security and license
description: How to report a vulnerability, what the runtime and build tools do with untrusted input, CI's read-only posture, and the licences covering the code and vendored assets.
section: project
order: 72
version: 0.7.0
sources: [SECURITY.md, LICENSE, fonts/vendor/LICENSE.txt, runtime/vendor/README.md, runtime/vendor/gsKit/dmaCore.h, packages/baker/pyproject.toml, packages/layout/package.json, runtime/ps2ui.c, .github/workflows/ci.yml, .github/workflows/hw.yml, .github/workflows/registry.yml]
---

# Security and license

## Reporting

Report a vulnerability privately through GitHub's "Report a vulnerability"
action on the Security tab of this repository. Do not open a public issue
for a vulnerability.

## Scope

`ps2ui_load` checks `size` against the header length before reading the
buffer, rejects a magic that is not `UIB1`, and rejects any version other
than the one it was built for. See every rejection code on
[errors and constants](page:runtime/errors-and-constants#error-codes) and
the exact order `ps2ui_load` runs them in on
[the load check order](page:runtime/errors-and-constants#load-check-order).
Validation does not make a blob trustworthy. Treat a `.uib` file from
someone else as untrusted input, the same as any other binary format a
program parses.

`ps2ui-layout` and `ps2ui-bake` run on the machine that invokes them and
read whatever HTML, CSS or IR file is pointed at them. Neither tool caps
memory or time against a hostile input today. Do not bake a project file
you would not open in a text editor first.

## CI

CI never grants write access to the default token. `ci.yml` sets:

```yaml
permissions:
  contents: read
```

`hw.yml` and `registry.yml` set the identical block. Every job in all three
workflows runs on a GitHub-hosted runner: `ubuntu-24.04` in `ci.yml`,
`ubuntu-24.04` in `hw.yml`, and hosted images in `registry.yml`
(`macos-15`, `macos-15-intel` and `windows-2025`, through a `matrix.os`
in three of its four jobs and a literal `runs-on` in the fourth). None
of the three declares a self-hosted runner. A
workflow run from a first-time contributor's pull request needs a
maintainer's approval before it starts, a GitHub repository setting rather
than a line in these files. Do not attach a self-hosted runner to this
repository; a workflow that can trigger from a pull request would then run
on it.

Runners for the check scripts, the example builds and the test suites live
in [contributing](page:project/contributing).

## Licences

| component | licence | file |
|---|---|---|
| Repository (this codebase) | MIT | [LICENSE](repo:LICENSE) |
| `ophtml` (Python package, `packages/baker`) | MIT | [pyproject.toml](repo:packages/baker/pyproject.toml#L10) |
| `@ophtml/layout` (npm package, `packages/layout`) | MIT | [package.json](repo:packages/layout/package.json#L9) |
| DejaVu fonts (`fonts/vendor/`) | Bitstream Vera License | [fonts/vendor/LICENSE.txt](repo:fonts/vendor/LICENSE.txt) |
| gsKit headers and `gsTexture.c` (`runtime/vendor/gsKit/`) | Academic Free License 2.0 | [runtime/vendor/README.md](repo:runtime/vendor/README.md#L7) |

The MIT licence in the repository root covers the runtime C sources, the
sample and the tooling outside the two packages. The Python package and the
npm package each carry the same MIT text in their own manifest, so a
consumer of either package sees the licence without opening the
repository.

DejaVu is not MIT. Its licence permits use, copy, merge, publish,
distribute and sale of the fonts, and requires a modified copy to drop the
names "Bitstream" and "Vera". `fonts/vendor/LICENSE.txt` carries the full
text.

The gsKit files under `runtime/vendor/gsKit/` are verbatim copies of public
ps2dev/gsKit headers plus one source file, kept so the host test suite
compiles against gsKit's real declarations. Each file carries an Academic
Free License 2.0 notice in its own header comment, for example
[dmaCore.h](repo:runtime/vendor/gsKit/dmaCore.h#L6). `runtime/vendor/README.md`
records the upstream commit these files were copied from and what the
vendoring does and does not guarantee about console behaviour; see
[internals](page:project/internals) for the reasoning behind the shim
policy.
