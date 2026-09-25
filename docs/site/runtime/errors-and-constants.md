---
id: runtime/errors-and-constants
title: Errors and constants
description: Every ps2ui error code with its value and trigger, the order ps2ui_load checks a blob, every public macro, the feature bits, and the build-time switches.
section: runtime
order: 43
version: 0.9.0
sources: [runtime/ps2ui.h, runtime/ps2ui.c, runtime/tests/test_runtime.c, runtime/tests/test_narrow.c, runtime/Makefile, runtime/sample/main.c, runtime/sample/Makefile, packages/baker/ps2ui_bake/vendor.py, packages/baker/ps2ui_bake/uib.py, tools/check-versions.py, docs/format-uib.md, README.md]
---

The runtime reports failure through fifteen integer codes declared in [runtime/ps2ui.h](repo:runtime/ps2ui.h#L424). Five functions return them: `ps2ui_load`, `ps2ui_tex_set`, `ps2ui_clut_set`, `ps2ui_theme_set` and `ps2ui_offset_set`. See [runtime/api-reference](page:runtime/api-reference#function-tables-by-group) for what every other function returns. Compare a return against the macro, not against the number. Handle a failure as [runtime/frame-loop](page:runtime/frame-loop#limits-and-errors) describes: a failed load or upload is fatal, a failed setter leaves the context as it was.

## Error codes

| code | value | triggered by | fix |
|---|---|---|---|
| `PS2UI_OK` | 0 | The call succeeded. | None. |
| `PS2UI_ERR_TRUNCATED` | -1 | `ps2ui_load`: `size` is below the 84-byte header, or a table or the string blob extends past `size` ([ps2ui.c](repo:runtime/ps2ui.c#L259), [ps2ui.c](repo:runtime/ps2ui.c#L316)). | Pass the whole file. Check the length the loader read. |
| `PS2UI_ERR_MAGIC` | -2 | `ps2ui_load`: the first four bytes are not `UIB1` ([ps2ui.c](repo:runtime/ps2ui.c#L266)). | The buffer is not a `.uib`. Check the path and the embedding step. |
| `PS2UI_ERR_VERSION` | -3 | `ps2ui_load`: the header version is not 7 ([ps2ui.c](repo:runtime/ps2ui.c#L268)). | Rebake with the toolchain that shipped this runtime. |
| `PS2UI_ERR_BOUNDS` | -4 | `ps2ui_load`: `n_screen` or `n_theme` is 0, or any table entry indexes past another table or past the string blob ([ps2ui.c](repo:runtime/ps2ui.c#L276) to [L472](repo:runtime/ps2ui.c#L472)). Also the answer to a NULL context from `ps2ui_clut_set`, `ps2ui_theme_set` and `ps2ui_offset_set`. | Run [cli/ps2ui-check](page:cli/ps2ui-check#the-catalogue) on the blob. A blob the baker wrote never trips this. |
| `PS2UI_ERR_TOO_MANY` | -5 | `ps2ui_load`: the counts are legal but the arena they add up to exceeds the target's address space ([ps2ui.c](repo:runtime/ps2ui.c#L485)). | The blob cannot load on a 32-bit target. Reduce slot capacities or slot count. |
| `PS2UI_ERR_CRC` | -6 | `ps2ui_load`: the CRC-32 over the file, with the `crc32` field read as zero, differs from the header ([ps2ui.c](repo:runtime/ps2ui.c#L320)). | The bytes changed after the bake. Recopy the file. |
| `PS2UI_ERR_FEATURES` | -7 | `ps2ui_load`: a feature bit outside `PS2UI_FEAT_KNOWN` ([ps2ui.c](repo:runtime/ps2ui.c#L270)), or a streamed texture in a blob without bit 3 ([ps2ui.c](repo:runtime/ps2ui.c#L357)). | Vendor the runtime that matches the baker. |
| `PS2UI_ERR_ALIGN` | -8 | `ps2ui_load`: the string blob address, a baked texture's `data_off`, or the arena is not 16-byte aligned ([ps2ui.c](repo:runtime/ps2ui.c#L342), [L365](repo:runtime/ps2ui.c#L365), [L489](repo:runtime/ps2ui.c#L489)). `ps2ui_tex_set`: the texel buffer is not 16-byte aligned ([L704](repo:runtime/ps2ui.c#L704)). | Declare the blob and the arena with `__attribute__((aligned(PS2UI_ARENA_ALIGN)))`. |
| `PS2UI_ERR_ARENA` | -9 | `ps2ui_load`: `arena` is NULL or `arena_size` is below `ps2ui_arena_size()` ([ps2ui.c](repo:runtime/ps2ui.c#L487)). | Size the arena from the bake transcript or from `ps2ui_arena_size`. |
| `PS2UI_ERR_NOT_STREAMED` | -10 | `ps2ui_tex_set`: a NULL argument, a name no texture carries, or a baked texture ([ps2ui.c](repo:runtime/ps2ui.c#L683) to [L693](repo:runtime/ps2ui.c#L693)). | Name a texture the bake marked streamed. |
| `PS2UI_ERR_SIZE` | -11 | `ps2ui_tex_set`: `len` differs from the entry's `data_len` ([ps2ui.c](repo:runtime/ps2ui.c#L698)). `ps2ui_clut_set`: `ncolors` exceeds the baked palette width ([L762](repo:runtime/ps2ui.c#L762)). | Pass exactly the reserved byte count. Read it from the texture table. |
| `PS2UI_ERR_RANGE` | -12 | `ps2ui_clut_set`: index at or past `n_clut` ([ps2ui.c](repo:runtime/ps2ui.c#L755)). `ps2ui_theme_set`: index at or past `n_theme` ([L791](repo:runtime/ps2ui.c#L791)). `ps2ui_offset_set`: a value outside -32768..32767 ([L1581](repo:runtime/ps2ui.c#L1581)). | Bound the argument by the header count or the int16 range. |
| `PS2UI_ERR_STATE` | -13 | `ps2ui_clut_set` before `ps2ui_upload` ([ps2ui.c](repo:runtime/ps2ui.c#L753)). | Call `ps2ui_upload` first. |
| `PS2UI_ERR_TINTS` | -14 | `ps2ui_load`: `n_theme` above 1 in a blob without `PS2UI_FEAT_ROLE_TINTS` ([ps2ui.c](repo:runtime/ps2ui.c#L294)). | Rebake. A themed blob must declare bit 4. |

`ps2ui_upload` does not use this table. It returns -1 when the texture footprint would pass 4 MiB of VRAM, and 0 otherwise ([ps2ui.c](repo:runtime/ps2ui.c#L597)). `ps2ui_arena_size` returns 0 for a blob it cannot size ([ps2ui.h](repo:runtime/ps2ui.h#L448)). The list queries `ps2ui_list_item_at` and `ps2ui_list_selected_row` return -1 for an empty or out-of-range row ([ps2ui.c](repo:runtime/ps2ui.c#L1707)).

The sample treats both entry points as fatal: a red screen for any load code, a yellow screen for an upload failure ([runtime/sample/main.c](repo:runtime/sample/main.c#L1673)).

## Load check order

`ps2ui_load` runs its checks in this order and returns at the first failure ([ps2ui.c](repo:runtime/ps2ui.c#L252)). The format side of each check is on [reference/uib-format](page:reference/uib-format#invariants).

1. `size` holds a header, else `PS2UI_ERR_TRUNCATED`.
2. Magic, else `PS2UI_ERR_MAGIC`.
3. Version, else `PS2UI_ERR_VERSION`.
4. No feature bit outside `PS2UI_FEAT_KNOWN`, else `PS2UI_ERR_FEATURES`.
5. `n_screen` is not 0, else `PS2UI_ERR_BOUNDS`.
6. `n_theme` is not 0, else `PS2UI_ERR_BOUNDS`.
7. `n_theme` above 1 requires bit 4, else `PS2UI_ERR_TINTS`.
8. Every table and the string blob end inside `size`, else `PS2UI_ERR_TRUNCATED`.
9. CRC-32, else `PS2UI_ERR_CRC`.
10. The string blob address is 16-aligned, else `PS2UI_ERR_ALIGN`.
11. Texture table: kind, format, CLUT index, name, data range and data alignment.
12. CLUT table: data range.
13. Command table: op, texture index, focus index, tint indices.
14. Focus table: the four links and the name.
15. Font table: texture index, baked kind, glyph and kern ranges.
16. Slot table: font, focus, tint indices, name and placeholder.
17. Screen table: command, focus and slot ranges, initial focus, name.
18. Screen 0's initial focus is in range.
19. The arena carve fits the address space, else `PS2UI_ERR_TOO_MANY`.
20. The arena is present and large enough, else `PS2UI_ERR_ARENA`.
21. The arena is 16-aligned, else `PS2UI_ERR_ALIGN`.

Steps 11 to 18 return `PS2UI_ERR_BOUNDS`, except a streamed texture without bit 3 in step 11, which returns `PS2UI_ERR_FEATURES`, and an unaligned baked texture, which returns `PS2UI_ERR_ALIGN`. The arena is written only after step 21, so a refused blob leaves it untouched ([test_runtime.c](repo:runtime/tests/test_runtime.c#L604)).

The CRC check sits before every per-table check. A blob with one corrupted field therefore reads as `PS2UI_ERR_CRC`, not as the code that field would earn. The test suite restamps the CRC with its `recrc` helper before every such check ([test_runtime.c](repo:runtime/tests/test_runtime.c#L52)).

Run the suite to see the loader checks fire.

```sh
make -C runtime test
```

```
ok 21 - bad magic rejected
ok 22 - truncated header rejected
ok 23 - truncated body rejected
ok 24 - wrong version rejected
ok 25 - corrupt body fails crc
ok 26 - unknown feature bits rejected
...
ok 62 - a blob at a non-16-aligned address is refused with PS2UI_ERR_ALIGN
...
ok 69 - load refuses an arena one byte short, so the size is exact
ok 70 - load refuses a NULL arena
ok 71 - load refuses a misaligned arena: the CLUT region is a DMA source
...
ok 372 - n_theme == 0 is refused: a themeless blob still has one row
ok 373 - n_theme > 1 without FEAT_ROLE_TINTS is refused by name, not loaded into a theme switch that cannot be correct
...
1..410
PASS: 410 checks, 0 failure(s)
```

## Constants

Every public macro comes from one grep over the header.

```sh
grep -n '#define PS2UI_' runtime/ps2ui.h
```

```
14:#define PS2UI_H
36:#define PS2UI_MAGIC   0x31424955u /* "UIB1" */
37:#define PS2UI_VERSION 7
42:#define PS2UI_FEAT_DYNAMIC_TEXT (1u << 0)
43:#define PS2UI_FEAT_KERNING      (1u << 1)
44:#define PS2UI_FEAT_SLOT_SPACING (1u << 2)
48:#define PS2UI_FEAT_STREAMED_TEX (1u << 3)
62:#define PS2UI_FEAT_ROLE_TINTS   (1u << 4)
63:#define PS2UI_FEAT_KNOWN     (PS2UI_FEAT_DYNAMIC_TEXT | PS2UI_FEAT_KERNING \
67:#define PS2UI_OP_QUAD          0
68:#define PS2UI_OP_TEXQUAD       1
69:#define PS2UI_OP_SCISSOR_PUSH  2
70:#define PS2UI_OP_SCISSOR_POP   3
72:#define PS2UI_STATE_ALWAYS     0
73:#define PS2UI_STATE_UNFOCUSED  1
74:#define PS2UI_STATE_FOCUSED    2
76:#define PS2UI_TEXFMT_PSMT8     0
77:#define PS2UI_TEXFMT_PSMCT32   1
79:#define PS2UI_NONE 0xFFFFu
133:#define PS2UI_TEXKIND_BAKED    0
134:#define PS2UI_TEXKIND_STREAMED 1
153:#define PS2UI_NAME_NONE 0xFFFFFFFFu
231:#define PS2UI_SLOT_ALIGN_LEFT   0
232:#define PS2UI_SLOT_ALIGN_CENTER 1
233:#define PS2UI_SLOT_ALIGN_RIGHT  2
234:#define PS2UI_SLOT_FLAG_ELLIPSIS 1
297:#define PS2UI_MAX_SCISSOR_DEPTH 8
301:#define PS2UI_LIST_NAME_MAX     64
412:#define PS2UI_OK              0
413:#define PS2UI_ERR_TRUNCATED  -1
414:#define PS2UI_ERR_MAGIC      -2
415:#define PS2UI_ERR_VERSION    -3
416:#define PS2UI_ERR_BOUNDS     -4
420:#define PS2UI_ERR_TOO_MANY   -5
421:#define PS2UI_ERR_CRC        -6
422:#define PS2UI_ERR_FEATURES   -7
423:#define PS2UI_ERR_ALIGN      -8  /* texture bytes or arena not 16-aligned */
424:#define PS2UI_ERR_ARENA      -9  /* arena smaller than ps2ui_arena_size() */
425:#define PS2UI_ERR_NOT_STREAMED -10 /* tex_set on a baked or unknown slot  */
426:#define PS2UI_ERR_SIZE       -11 /* tex_set payload is not the reservation */
427:#define PS2UI_ERR_RANGE      -12 /* a setter's argument is out of range    */
428:#define PS2UI_ERR_STATE      -13 /* clut_set before ps2ui_upload            */
429:#define PS2UI_ERR_TINTS      -14 /* n_theme > 1 without PS2UI_FEAT_ROLE_TINTS */
434:#define PS2UI_ARENA_ALIGN    16
714:#define PS2UI_VISIBLE_UNKNOWN (-1)
```

| name | value | meaning |
|---|---|---|
| `PS2UI_MAGIC` | `0x31424955` | The first four bytes of a `.uib`, `UIB1` in little-endian order. |
| `PS2UI_VERSION` | 7 | The `.uib` format version this runtime reads. |
| `PS2UI_NONE` | `0xFFFF` | An empty 16-bit index: no focus, no CLUT, no neighbour. |
| `PS2UI_NAME_NONE` | `0xFFFFFFFF` | A texture with no name. Offset 0 is a real string, so 0 cannot mean none. |
| `PS2UI_ARENA_ALIGN` | 16 | Required alignment of the arena. The CLUT pool at its start is a DMA source. |
| `PS2UI_MAX_SCISSOR_DEPTH` | 8 | Depth of the scissor stack in `ps2ui_render`. A deeper push is refused and counted in `stats.scissor_overflow`. |
| `PS2UI_LIST_NAME_MAX` | 64 | Size of the stack buffer that builds a row focus name in `ps2ui_list_move`. |
| `PS2UI_VISIBLE_UNKNOWN` | -1 | `ps2ui_visible_get` answer for a name the current screen lacks. |
| `PS2UI_OP_QUAD` | 0 | Command op: untextured quad. |
| `PS2UI_OP_TEXQUAD` | 1 | Command op: textured quad. |
| `PS2UI_OP_SCISSOR_PUSH` | 2 | Command op: push a clip rectangle. |
| `PS2UI_OP_SCISSOR_POP` | 3 | Command op: pop the clip rectangle. |
| `PS2UI_STATE_ALWAYS` | 0 | Command state: drawn whatever the focus. |
| `PS2UI_STATE_UNFOCUSED` | 1 | Command state: drawn when its focus node is not focused. |
| `PS2UI_STATE_FOCUSED` | 2 | Command state: drawn when its focus node is focused. |
| `PS2UI_TEXFMT_PSMT8` | 0 | Texture format: 8-bit indexed with a CLUT. |
| `PS2UI_TEXFMT_PSMCT32` | 1 | Texture format: 32-bit RGBA. |
| `PS2UI_TEXKIND_BAKED` | 0 | Texture kind: texels live in the blob. |
| `PS2UI_TEXKIND_STREAMED` | 1 | Texture kind: texels arrive through `ps2ui_tex_set`. |
| `PS2UI_SLOT_ALIGN_LEFT` | 0 | Slot text alignment. |
| `PS2UI_SLOT_ALIGN_CENTER` | 1 | Slot text alignment. |
| `PS2UI_SLOT_ALIGN_RIGHT` | 2 | Slot text alignment. |
| `PS2UI_SLOT_FLAG_ELLIPSIS` | 1 | Slot flag bit 0: overflow ends in an ellipsis. |

`PS2UI_MAX_SCISSOR_DEPTH` is the only fixed-size limit in the runtime ([ps2ui.h](repo:runtime/ps2ui.h#L283)). Table counts are bounded by the header's `uint16` fields, and the context is sized from the blob through the arena. Two comments in `ps2ui.c` still name table caps that no longer exist ([ps2ui.c](repo:runtime/ps2ui.c#L658), [L1646](repo:runtime/ps2ui.c#L1646)); no such macro is defined.

```sh
grep -n 'define PS2UI_MAX' runtime/ps2ui.h runtime/ps2ui.c
```

```
runtime/ps2ui.h:297:#define PS2UI_MAX_SCISSOR_DEPTH 8
```

`PS2UI_VERSION` is the format version, pledged frozen at 7 ([docs/format-uib.md](repo:docs/format-uib.md#L385)). It does not track runtime releases and no longer moves when `ps2ui.c` changes ([vendor.py](repo:packages/baker/ps2ui_bake/vendor.py#L190)). The baker's writer carries the same number ([uib.py](repo:packages/baker/ps2ui_bake/uib.py#L49)), and `tools/check-versions.py` holds the two equal in the tree ([check-versions.py](repo:tools/check-versions.py#L400)). Baker and runtime match in a project because `ps2ui vendor-runtime` ships both files from one installed package, not because of the macro.

## Feature bits

A feature bit in the header names a capability the reader must have. `ps2ui_load` refuses a blob with a bit outside `PS2UI_FEAT_KNOWN` ([ps2ui.h](repo:runtime/ps2ui.h#L63)). The baker sets each bit under the same rule from [uib.py](repo:packages/baker/ps2ui_bake/uib.py#L356).

| name | value | set when | load rule |
|---|---|---|---|
| `PS2UI_FEAT_DYNAMIC_TEXT` | 1 | The blob has a font table or a slot table. | None beyond `FEAT_KNOWN`. |
| `PS2UI_FEAT_KERNING` | 2 | Any font carries kern pairs. | None beyond `FEAT_KNOWN`. |
| `PS2UI_FEAT_SLOT_SPACING` | 4 | Any slot has non-zero `letter_spacing`. | None beyond `FEAT_KNOWN`. |
| `PS2UI_FEAT_STREAMED_TEX` | 8 | Any texture has kind `STREAMED`. | Required by every streamed entry, else `PS2UI_ERR_FEATURES` ([ps2ui.c](repo:runtime/ps2ui.c#L357)). |
| `PS2UI_FEAT_ROLE_TINTS` | 16 | The blob carries more than one theme row ([uib.py](repo:packages/baker/ps2ui_bake/uib.py#L377)). | Required when `n_theme` exceeds 1, else `PS2UI_ERR_TINTS` ([ps2ui.c](repo:runtime/ps2ui.c#L294)). |
| `PS2UI_FEAT_KNOWN` | 31 | The OR of the five bits above. | Any other bit set returns `PS2UI_ERR_FEATURES` ([ps2ui.c](repo:runtime/ps2ui.c#L270)). |

## Build-time switches

Four macros change how `ps2ui.c` compiles. Pass them with `-D`. Three are falsification arms for bench sessions and are never defined in a shipping build. The sample Makefile exposes them as `LINEAR_CLUT=1`, `NO_SYNC=1` and `NO_ALPHA=1` ([runtime/sample/Makefile](repo:runtime/sample/Makefile#L58)).

| macro | default | effect | exercised by |
|---|---|---|---|
| `PS2UI_CLUT_PERMUTE` | 1 | 0 uploads every CLUT in linear order instead of CSM1 order ([ps2ui.c](repo:runtime/ps2ui.c#L537)). | `make -C runtime test` syntax-check compiles `-DPS2UI_CLUT_PERMUTE=0` ([Makefile](repo:runtime/Makefile#L170)). |
| `PS2UI_ARENA_LIMIT` | `SIZE_MAX` of the target | Caps the arena carve. The build fails if the value is wider than `size_t` ([ps2ui.c](repo:runtime/ps2ui.c#L117)). Narrow only. | `make -C runtime test-narrow` compiles `-DPS2UI_ARENA_LIMIT=0xFFFFFFFFull` ([Makefile](repo:runtime/Makefile#L317)). |
| `PS2UI_PRIMALPHA_OFF` | undefined | Defined: `ps2ui_render` sets `PrimAlphaEnable` off, so glyph alpha is ignored ([ps2ui.c](repo:runtime/ps2ui.c#L1051)). | syntax-check compiles `-DPS2UI_PRIMALPHA_OFF` ([Makefile](repo:runtime/Makefile#L174)). |
| `PS2UI_SKIP_SYNCDCACHE` | undefined | Defined: `ps2ui_tex_set` skips the data-cache writeback, so the GIF may read stale texels ([ps2ui.c](repo:runtime/ps2ui.c#L717)). | syntax-check compiles `-DPS2UI_SKIP_SYNCDCACHE` ([Makefile](repo:runtime/Makefile#L181)). |

`PS2UI_ARENA_LIMIT` exists so the 64-bit host suite can model the 32-bit EE. The narrow build feeds the runtime a well-formed blob whose carve passes 4 GiB and the memcard example blob, and expects one refusal and one load.

```sh
make -C runtime test-narrow
```

```
./build/test_narrow ../examples/memcard/build/ui.uib build/huge.uib
ok 1 - a carve past the target's address width is reported as 0, not as a wrapped small number
ok 2 - and ps2ui_load refuses it by name rather than carving
ok 3 - an ordinary blob still gets an arena at this width
ok 4 - and still loads
ok 5 - and is usable afterwards
1..5
PASS: 5 checks, 0 failure(s)
```
