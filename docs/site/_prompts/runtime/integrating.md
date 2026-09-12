# Page: runtime/integrating (Integrating the runtime)

Page type: `guide`. Section order: `40`. Wave: `2`.

## Purpose and audience

Getting `ps2ui.c` and `ps2ui.h` into a project and compiling them: vendor-runtime's behaviour, the cross toolchain, the Makefile lines, the gsKit pin, the sample Makefile's flags, and the host-side test targets that exist.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui.md`, `_facts/runtime/api-reference.md`, `_facts/runtime/errors-and-constants.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
3. The drift rows below. A page documents the truth column and never repeats the claim column.

### Voice and format (from ARCHITECTURE.md, binding)

- Imperative mood for instructions, present tense for behaviour. "Run `ps2ui build`." Never "you can run".
- Forbidden: let's, we, we'll, in this section, in this guide, simply, seamless, seamlessly, robust, leverage, powerful, note that, it's worth noting, keep in mind, as you can see, of course, essentially, basically, easily, straightforward, delve, dive into, unlock, empower, journey, crucial, vital. No emoji, no exclamation marks, no rhetorical questions.
- Lead with what the thing does and how to use it. Say why only when the reason changes what the reader does, in at most two sentences. Longer reasons are a link to `project/internals` or a `repo:` link.
- One fact per sentence, under 25 words. No em dashes.
- Flags, keys, functions, error codes and attributes live in tables with the column set named under Page structure. Prose never restates a table.
- Every code block comes from a command run in this session or a file in the tree. Output blocks are real output, trimmed with `...` only where the trimmed lines are irrelevant.
- Numbers appear only when a command in this session produced them, and the command sits beside them.
- Do not copy README.md sentences. Re-derive from code and restate.
- A feature new in 0.6.0 opens its section with `New in 0.6.0.` Nothing else carries a version.
- 300 to 1500 words of prose plus tables.
- Links: `[text](page:<id>#<anchor>)` for pages, `[path](repo:<path>#L<n>)` for repository files. Kebab-case anchors.

### Environment (run first, stop on failure)

```sh
python3 -m pip install Pillow
pip install -e packages/baker
(cd packages/layout && npm link)
python3 tools/check-versions.py --except-tag
./examples/memcard/build.sh
```

`ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen`, `ps2ui-layout`, `ps2ui-dev` are then on PATH and point at this tree. Pages show the installed spelling. The checkout spelling (`PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui`, `node packages/layout/bin/ps2ui-layout.js`) appears only on `cli/ps2ui` under "From a checkout".

When code, tests, a repository doc and README.md disagree, the order of authority is: code, then tests, then `docs/*.md`, then README.md. Cite the code line in the facts file.

### Known drift touching this page

| tag | where the stale claim lives | claim | truth |
|---|---|---|---|
| D1 | README.md Tests section; CONTRIBUTING.md | `make -C runtime test test-compat`; `PS2UI_GSKIT_HAS_FUNCTION=0` | No such target or macro. Targets: `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. gsKit has no per-texture TFX field (BACKLOG.md F28). |
| D12 | README.md Quick start C comment | `PS2UI_VERSION` keeps baker and runtime from drifting | It is the frozen format version, 7. Baker and runtime match because `ps2ui vendor-runtime` ships both files from one package. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/ps2ui_bake/vendor.py - FILES, find_source, drift classification, messages
- runtime/Makefile - targets and the -S argument
- runtime/sample/Makefile - flags and the pairing guards
- runtime/vendor/README.md - gsKit pin, what host tests do and do not prove
- packages/baker/README.md 'Getting it onto a console'; tools/check-runtime-shipped.py
- packages/baker/tests/test_vendor.py

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. vendor-runtime writes exactly two files, labels its source, refuses drifted files without --force all-or-nothing, prints the docker line and Makefile lines only when it wrote something -> run into a temp dir twice, edit ps2ui.h, run again; paste all three outputs
2. The wheel carries the runtime -> run `python3 tools/check-runtime-shipped.py` and paste
3. Cross toolchain: ghcr.io/ps2dev/ps2dev, gsKit at $PS2DEV/gsKit not on the include path, the three Makefile lines -> quote from vendor.py output
4. gsKit pinned at commit 43122eb; PS2SDK floats -> cite vendor/README.md and hw.yml
5. Host targets: test (includes test-narrow), syntax-check (11 variants, -S), timing-check, clean; no test-compat -> run `make -C runtime test` and `make -C runtime syntax-check CC=clang`, paste the tails
6. Sample Makefile flags and their pairing constraints -> read the $(error) guards; table them
7. Host tests prove struct shape and prototypes, not GS behaviour -> cite vendor/README.md

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: `ps2ui vendor-runtime src/` and the three Makefile lines. Reference table 1: vendor-runtime (option · effect). Table 2: sample Makefile flags (flag · builds · requires). Table 3: host targets. Behaviour: source labels, drift, the toolchain. Limits.

Frontmatter:

```yaml
---
id: runtime/integrating
title: Integrating the runtime
description: <one sentence>
section: runtime
order: 40
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui - vendor-runtime
- runtime/frame-loop - after integrating
- runtime/deploying - after building
- runtime/first-boot - MINIMAL and PROBE
- project/contributing - test targets

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `integrate.vendor.behaviour`
- `integrate.toolchain` - docker line and Makefile lines
- `integrate.make.flags` - the sample table
- `integrate.test-targets` - the real list
- `integrate.gskit-pin`

## Out of scope

- deploying to a card -> runtime/deploying

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/integrating.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/integrating/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/integrating`, `title`, `description`, `section`, `order: 40`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
