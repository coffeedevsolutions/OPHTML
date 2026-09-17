# facts: index

This page emits no new facts. It consolidates facts its parents already
verified. No command ran in this session; every row below restates a
parent fact id, unchanged, and names the parent facts file it came from.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| install.requirements | Node.js needs 18 or newer, Python needs 3.9 or newer, Pillow needs 9 or newer. Raqm and fribidi are needed only for `ps2ui fontgen`. The ps2dev toolchain is needed only for the console half. | getting-started/installation | restated from `_facts/getting-started/installation.md`, row `install.requirements`, itself read from packages/layout/package.json and packages/baker/pyproject.toml | verified |
| loop.order | The runtime lifecycle: size the arena, declare it, `ps2ui_load`, `ps2ui_upload` once, then per frame clear, `ps2ui_render`, flip | getting-started/how-it-works | restated from `_facts/getting-started/how-it-works.md`, row `loop.order`, itself restating parent fact `loop.order` in `_facts/runtime/frame-loop.md` | verified |
| compat.versions | The tree carries five version numbers: `ophtml` (PyPI) 0.7.0, `@ophtml/layout` (npm) 0.7.0, the ui.json IR 1, the `.uib` format 7, and the runtime macro `PS2UI_VERSION` 7. `check-versions.py` holds all five to each other. | reference/compatibility | restated from `_facts/reference/compatibility.md`, row `compat.versions`, verified there by `python3 tools/check-versions.py --except-tag` | verified |

## disputes

None. No parent fact was found wrong.
