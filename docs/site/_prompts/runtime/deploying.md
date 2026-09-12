# Page: runtime/deploying (Deploying)

Page type: `guide`. Section order: `47`. Wave: `3`.

## Purpose and audience

From an ELF to a console: what gets copied, the emulator first, the build, the card and USB paths, launching, autoboot, and reading a flat-colour screen. Keeps the bench/practice markers.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/runtime/integrating.md`, `_facts/runtime/first-boot.md`, `_facts/runtime/streaming-art.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- docs/deploying.md - the whole file; restate, do not copy
- tools/check-deploying.py - which claims are checked (status fills, Makefile flags)
- runtime/sample/main.c - the status fill literals
- runtime/sample/Makefile - MINIMAL, STATIC, SCREEN

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. The four status fills and their meaning come from main.c literals -> run `python3 tools/check-deploying.py`; table them from the source
2. Every build flag named exists -> grep the Makefile
3. Emulators: Play! (CI, bench), PCSX2 software renderer (practice) -> cite deploying.md and hw.yml
4. Memory-card, USB, OPL and autoboot paths carry [practice]; the SCPH-50000 USB path carries [bench] -> keep the markers as a legend table

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Minimal example: the make line and the docker line. Reference table: path · marker · steps. Table 2: screen colour · meaning. Behaviour: emulator, card devices, launching, autoboot. Limits: what is bench and what is practice.

Frontmatter:

```yaml
---
id: runtime/deploying
title: Deploying
description: <one sentence>
section: runtime
order: 47
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- runtime/integrating - building
- runtime/first-boot - the checklist
- runtime/streaming-art - USB for streamed art
- examples/channel6 - the channel layout

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `deploy.paths`
- `deploy.status-fills`

## Out of scope

- the hardware log -> project/internals

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/runtime/deploying.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/runtime/deploying/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: runtime/deploying`, `title`, `description`, `section`, `order: 47`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
