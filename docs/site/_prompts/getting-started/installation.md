# Page: getting-started/installation (Installation)

Page type: `guide`. Section order: `1`. Wave: `3`.

## Purpose and audience

Someone with a laptop and a TTF gets both packages installed and proves it with `--version`. They learn which half needs a cross toolchain and which does not, and what to do when `ps2ui fontgen` refuses on macOS.

## Read first

1. `docs/site/ARCHITECTURE.md`, all of it. The rules below are copied from it and are binding.
2. Parent facts files, before opening any source: `_facts/cli/ps2ui.md`, `_facts/cli/ps2ui-fontgen.md`, `_facts/reference/compatibility.md`, `_facts/runtime/integrating.md`. Reuse their fact ids; do not restate a parent fact differently. If one is wrong, write a `## disputes` section and stop.
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
| D10 | packages/baker/ps2ui_bake/serve.py `prog="ps2ui-serve"` | a `ps2ui-serve` command | Not installed. The command is `ps2ui serve`. |

## Sources of truth

Line numbers are hints from the exploration that produced this brief; re-locate by symbol name. Authority order: code, tests, docs/*.md, README.md.

- packages/baker/pyproject.toml - name, requires-python, dependencies, console scripts
- packages/layout/package.json - name, bin, engines, publishConfig
- packages/baker/ps2ui_bake/fontgen.py `_raqm_remedy` and `_rebuild_hint` - the refusal text and per-platform remedy
- packages/baker/ps2ui_bake/ps2ui.py lines 36-57 - how `ps2ui build` finds the layout compiler (`PS2UI_LAYOUT`, PATH, checkout)
- fonts/fonts.json - candidate paths; the vendored DejaVu pair exists only in a checkout
- .github/workflows/registry.yml - what a from-registry install proves on ubuntu and macOS
- docs/tutorial-uc3.md section 1 blockquote - the fribidi finding; restate, do not copy

## Claims to verify, and how

Each item is `claim -> how to prove it`. Run every command. Paste real output into the page where the structure calls for it and record the result in the facts file.

1. `pip install ophtml` installs `ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen` -> read `[project.scripts]`; run `ps2ui --version` and paste
2. `npm install -g @ophtml/layout` installs `ps2ui-layout` and `ps2ui-dev` -> read `bin`; run `ps2ui-layout --version` and paste
3. Node >= 18, Python >= 3.9, Pillow >= 9 -> read `engines` and `requires-python`/`dependencies`
4. `ps2ui fontgen` refuses without Raqm and prints a platform remedy that checks fribidi separately -> run `python3 -c "from PIL import features; print(features.check('raqm'), features.check('fribidi'))"`; run `python3 -m unittest tests.test_baker.TestFontgenRefusesWithoutRaqm -v` from packages/baker; quote the remedy text from `fontgen.py` and mark the fact `code-only` if this machine has Raqm
5. Layout compiler discovery order is `$PS2UI_LAYOUT`, then `ps2ui-layout` on PATH, then a sibling checkout -> read ps2ui.py; run `PS2UI_LAYOUT=/bin/false ps2ui build` on the memcard example and paste the error
6. From a checkout: `pip install -e packages/baker` puts the four commands on PATH -> run it and `which ps2ui`
7. The console half needs ps2dev; nothing else does -> cite integrate.vendor.behaviour from runtime/integrating

## Screenshots

None. Do not add decorative images.

## Page structure

Skeleton for type `guide`: What it is · Minimal example · Reference table · Behaviour · Limits and errors · Related pages.

Guide skeleton. Reference table is 'What you need' (need · minimum · why). Then 'Install the packages', 'Verify', 'Fonts', 'If fontgen refuses' (the remedy as a table: platform · first thing to try · then), 'From a checkout', 'The console half'.

Frontmatter:

```yaml
---
id: getting-started/installation
title: Installation
description: <one sentence>
section: getting-started
order: 1
version: 0.6.0
sources: [<every repository path opened>]
---
```

## Cross-links

Write links as `[text](page:<id>#<anchor>)`. Every id below must appear on the page at the place named.

- cli/ps2ui-fontgen - Fonts
- runtime/integrating - The console half
- reference/compatibility - What you need
- getting-started/quickstart - Related pages

## Facts to emit

Write `_facts/<page-id>.md` before writing the page:

```markdown
# facts: <page-id>

| id | fact | source | verified by | status |
|---|---|---|---|---|
```

Status is `verified` (a command or test in this session proved it), `code-only` (read in source; say why nothing executable exists), or `contradicts-readme` (verified, and README.md says otherwise; cite the README line). If a parent fact is wrong, append `## disputes` with the id and evidence, and stop.

Required ids (downstream pages read these by name):

- `install.commands` - the two install lines and the two verify lines with their output
- `install.requirements` - the need/minimum table
- `install.raqm.remedy` - the per-platform remedy table

## Out of scope

- fontgen arguments -> cli/ps2ui-fontgen
- the cross toolchain and Makefile -> runtime/integrating

## Done when

- [ ] Environment block ran clean.
- [ ] `_facts/getting-started/installation.md` exists with every fact id listed under "Facts to emit", each with a status.
- [ ] Every command shown on the page was run in this session; every output block is pasted from that run.
- [ ] Every screenshot listed exists under `assets/getting-started/installation/`, is registered in `assets/assets.json` with its command, and has alt text.
- [ ] Frontmatter present: `id: getting-started/installation`, `title`, `description`, `section`, `order: 1`, `version: 0.6.0`, `sources` (every path opened).
- [ ] Every `page:` link names an id from the page index in ARCHITECTURE.md.
- [ ] Word count of prose is 300 to 1500 (`pandoc -t plain` or a `wc -w` after stripping tables and code).
- [ ] Forbidden-phrase grep over the page returns nothing.
- [ ] Nothing from the drift rows' "claim" column appears on the page.
- [ ] Sections appear in the order given under Page structure and every table has the named columns.
