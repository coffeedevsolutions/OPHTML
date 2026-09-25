# facts: project/security-and-license

No parent facts files. This page is a wave-0-style leaf: every claim below
comes directly from code and repository documents opened in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| security.reporting | Report a vulnerability privately via GitHub's "Report a vulnerability" (Security tab) rather than a public issue | SECURITY.md:5-6 | read the file | code-only |
| security.load.validates | ps2ui_load checks size against the header before touching the buffer, checks the magic, and rejects any version not equal to PS2UI_VERSION | runtime/ps2ui.c:256-269 | read the function; matches runtime/errors-and-constants Error codes and Load check order | verified |
| security.load.untrusted | SECURITY.md states blobs from strangers are untrusted input even though the loader validates offsets, counts and terminators, and names a fuzz harness as backlog item S2 | SECURITY.md:10-14 | read the file | code-only |
| security.build.tools.caps | SECURITY.md states resource-exhaustion caps for hostile HTML/CSS/IR input to ps2ui-layout and ps2ui-bake are planned as backlog item S3 and do not exist yet | SECURITY.md:15-18 | read the file | code-only |
| ci.permissions.readonly | ci.yml's top-level permissions block grants only contents: read | .github/workflows/ci.yml:9-10 | read the file | verified |
| ci.permissions.allhosted | Every job across ci.yml, hw.yml and registry.yml runs on a GitHub-hosted runner (ubuntu-24.04, or a matrix.os over macos-15, macos-15-intel and windows-2025) and every workflow's permissions block is contents: read | .github/workflows/ci.yml:54,95,9-10; .github/workflows/hw.yml:31,51,190,777; .github/workflows/registry.yml:36,87,213,267,390 | grep runs-on and permissions across the three workflow files | verified |
| license.packages.mit | The repository root LICENSE is the MIT License, copyright coffeedevsolutions | LICENSE:1-3 | read the file | verified |
| license.baker.mit | packages/baker/pyproject.toml declares license = { text = "MIT" } for the ophtml package | packages/baker/pyproject.toml:10 | read the file | verified |
| license.layout.mit | packages/layout/package.json declares "license": "MIT" for @ophtml/layout | packages/layout/package.json:9 | read the file | verified |
| license.dejavu | fonts/vendor/LICENSE.txt licenses the DejaVu fonts under the Bitstream Vera license, a separate permissive font license with its own renaming condition | fonts/vendor/LICENSE.txt:1-51 | read the file | verified |
| license.gskit | runtime/vendor/README.md states runtime/vendor/gsKit/ holds verbatim ps2dev/gsKit headers and gsTexture.c licensed under the Academic Free License version 2.0, and each vendored header carries its own notice | runtime/vendor/README.md:1-7; runtime/vendor/gsKit/dmaCore.h:6 | read both files | verified |
