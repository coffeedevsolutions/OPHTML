---
id: cli/ps2ui-fontgen
title: ps2ui-fontgen
description: Measure a TTF into the metrics JSON that the layout compiler and the baker share.
section: cli
order: 34
version: 0.9.0
sources: [packages/baker/ps2ui_bake/fontgen.py, packages/baker/ps2ui_bake/ps2ui.py, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/__init__.py, packages/baker/pyproject.toml, packages/baker/tests/test_baker.py, fonts/regen.sh, fonts/fonts.json, fonts/default.metrics.json, fonts/default-bold.metrics.json, README.md, docs/site/ARCHITECTURE.md]
---

# ps2ui-fontgen

`ps2ui-fontgen` measures one TrueType face and writes one metrics JSON file. The layout compiler sizes text from that file and the baker draws text from it, so both stages agree on every advance and kern pair. `ps2ui fontgen` wraps the bare tool to produce both weights of a project and the manifest that names them. The measured values drive everything described on [Text and fonts](page:authoring/text-and-fonts#behaviour).

The bare tool is `ps2ui_bake.fontgen:main` and the wrapper is `ps2ui_bake.ps2ui:main`, both from [pyproject.toml](repo:packages/baker/pyproject.toml#L21).

## ps2ui-fontgen

### Synopsis

```
ps2ui-fontgen <font.ttf> <family> <weight> <out.metrics.json> [charset-file]
ps2ui-fontgen --version
```

Run it against the vendored regular face:

```sh
ps2ui-fontgen fonts/vendor/DejaVuSans.ttf "DejaVu Sans" 400 default.metrics.json
```

```
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> default.metrics.json
```

The summary line goes to stderr. Nothing goes to stdout except the version:

```sh
ps2ui-fontgen --version
```

```
ps2ui-fontgen 0.9.0
```

The version check runs before every other check, so it cannot fail for a missing font or a missing dependency. See [main](repo:packages/baker/ps2ui_bake/fontgen.py#L145).

### Options

All four required arguments are positional. Order matters.

| flag | argument | default | effect |
|---|---|---|---|
| (1st) | `<font.ttf>` | required | the TrueType file to measure; passed to `PIL.ImageFont.truetype` |
| (2nd) | `<family>` | required | copied verbatim into the `family` field |
| (3rd) | `<weight>` | required | parsed with `int()` and copied into the `weight` field |
| (4th) | `<out.metrics.json>` | required | the file to write; overwritten if present |
| (5th) | `[charset-file]` | built-in charset | a UTF-8 file whose whole contents replace the built-in charset |
| `--version`, `-V` | none | off | print `ps2ui-fontgen <version>` to stdout and exit 0; only honoured as the first argument |

The built-in charset is `DEFAULT_CHARSET` at [fontgen.py](repo:packages/baker/ps2ui_bake/fontgen.py#L23). It is the space, `string.printable` without its whitespace, and twenty extra characters. Print the extras by codepoint:

```sh
python3 -c "from ps2ui_bake.fontgen import DEFAULT_CHARSET as C; s=sorted(set(C)); print(len(s), 'codepoints'); print([ord(c) for c in s if ord(c) > 126])"
```

```
115 codepoints
[160, 183, 215, 8211, 8212, 8216, 8217, 8220, 8221, 8230, 8592, 8593, 8594, 8595, 9633, 9651, 9671, 9675, 10003, 10005]
```

| codepoint | character |
|---|---|
| U+00A0 | no-break space |
| U+00B7 | middle dot |
| U+00D7 | multiplication sign |
| U+2013, U+2014 | en dash, em dash |
| U+2018, U+2019 | left and right single quotation marks |
| U+201C, U+201D | left and right double quotation marks |
| U+2026 | horizontal ellipsis |
| U+2190 to U+2193 | left, up, right, down arrows |
| U+25A1, U+25B3, U+25C7, U+25CB | white square, triangle, diamond, circle |
| U+2713, U+2715 | check mark, multiplication x |

A charset file is read whole. Duplicates collapse and codepoints below 32 are dropped, so a trailing newline is harmless. A file holding `ABC` and a newline produces this:

```sh
printf 'ABC\n' > abc.txt
ps2ui-fontgen fonts/vendor/DejaVuSans.ttf "DejaVu Sans" 400 abc.metrics.json abc.txt
```

```
ps2ui-fontgen: 3 glyphs, 3 kern pairs -> abc.metrics.json
```

Include every character the project's HTML uses. A codepoint outside the charset is drawn at the `missing` width.

### Output

The metrics file is one JSON object written with `indent=1` and `sort_keys=True`, so codepoint keys sort as strings. Print its keys:

```sh
python3 -c "import json; print(sorted(json.load(open('fonts/default.metrics.json')).keys()))"
```

```
['advances', 'ascent', 'descent', 'family', 'kerning', 'missing', 'source', 'unitsPerEm', 'weight']
```

The values below come from `fonts/default.metrics.json`, printed by:

```sh
python3 -c "import json; d=json.load(open('fonts/default.metrics.json')); print({k:(len(v) if isinstance(v,dict) else v) for k,v in d.items()})"
```

```
{'advances': 115, 'ascent': 929, 'descent': 236, 'family': 'DejaVu Sans', 'kerning': 284, 'missing': 531, 'source': 'DejaVuSans.ttf', 'unitsPerEm': 1000, 'weight': 400}
```

| field | type | value in fonts/default.metrics.json | meaning |
|---|---|---|---|
| `family` | string | `"DejaVu Sans"` | the `<family>` argument, verbatim |
| `weight` | integer | `400` | the `<weight>` argument |
| `unitsPerEm` | integer | `1000` | always 1000; the face is loaded at a 1000px em |
| `ascent` | integer | `929` | `font.getmetrics()[0]` at that em |
| `descent` | integer | `236` | `font.getmetrics()[1]` at that em |
| `advances` | object | 115 entries | decimal codepoint string to advance in units per 1000/em, rounded to an integer |
| `kerning` | object | 284 entries | `"prev,cur"` codepoint pair to a signed integer adjustment in the same units; only non-zero pairs |
| `missing` | integer | `531` | the advance of `?`, or 500 when `?` is not in the charset |
| `source` | string | `"DejaVuSans.ttf"` | the TTF path after its last `/` |

Advances are measured at a 1000px em so hinting cannot perturb them differently at different sizes. Both stages then derive pixel advances with the same rounding, described on [Text and fonts](page:authoring/text-and-fonts#behaviour).

Kerning is measured, not read from a `kern` or `GPOS` table. For every ordered pair the tool shapes `a + b`, `a` and `b` with HarfBuzz, through the `uharfbuzz` package, and stores the rounded difference when it is non-zero; HarfBuzz applies whichever of the two tables the font carries. Substitution features `liga`, `clig`, `dlig`, `hlig`, `rlig` and `calt` are turned off for those calls, so a ligature such as `ff` is not recorded as a kern. See [NO_SUBSTITUTION](repo:packages/baker/ps2ui_bake/fontgen.py#L39) and [build_kerning](repo:packages/baker/ps2ui_bake/fontgen.py#L102). The table is directional: `84,111` (`To`) is present and `111,84` is not.

### Exit codes

| code | triggered by | fix |
|---|---|---|
| 0 | metrics written | none |
| 2 | fewer than four positional arguments | supply `<font.ttf> <family> <weight> <out.metrics.json>` |
| 1 | `<weight>` is not an integer (`ValueError` traceback) | pass a number such as `400` or `700` |
| 1 | the TTF cannot be opened (`OSError: cannot open resource` traceback) | check the path |
| 1 | `uharfbuzz` is not installed, which only a checkout can be | `pip install uharfbuzz` |

There is no Raqm check. Up to 0.8.0 the tool measured through Pillow's Raqm layout engine, which loads fribidi from the machine, so a stock macOS or Windows install refused to write anything; that refusal is on [Installation](page:getting-started/installation#if-fontgen-refuses), where upgrading is the fix. HarfBuzz reproduces the tables Raqm measured exactly, so no committed metrics file changed. `TestFontgenNeedsNoRaqm` at [test_baker.py](repo:packages/baker/tests/test_baker.py#L157) tells Pillow it has no Raqm and requires the committed tables byte for byte.

`uharfbuzz` is imported only when a font is measured, so a checkout without it loses this one command, with one line naming the package to install, and nothing is written.

### Files written

| file | content |
|---|---|
| `<out.metrics.json>` | the metrics object above, one file per face |

The shipped metrics live in `fonts/` and are committed rather than built, so a checkout with no TTF still lays text out identically. Regenerate them after changing `fontgen.py`:

```sh
./fonts/regen.sh
```

```
regen: regular = /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> /home/user/OPHTML/fonts/default.metrics.json
regen: bold = /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
ps2ui-fontgen: 115 glyphs, 163 kern pairs -> /home/user/OPHTML/fonts/default-bold.metrics.json
```

```sh
git diff --exit-code fonts/; echo $?
```

```
0
```

The script reads [fonts/fonts.json](repo:fonts/fonts.json) through `load_font_manifest` in [cli.py](repo:packages/baker/ps2ui_bake/cli.py#L83), which takes the first candidate path that exists. It passes the family `DejaVu Sans`. The vendored copy under `fonts/vendor/` yields the same bytes as the system DejaVu.

## ps2ui fontgen

### Synopsis

```
ps2ui fontgen <regular> <bold> [-o DIR]
```

Run it against the vendored faces:

```sh
ps2ui fontgen fonts/vendor/DejaVuSans.ttf fonts/vendor/DejaVuSans-Bold.ttf -o out
```

```
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> out/default.metrics.json
ps2ui-fontgen: 115 glyphs, 163 kern pairs -> out/default-bold.metrics.json
ps2ui-fontgen: manifest -> out/fonts.json
```

All three lines go to stderr. The implementation is `cmd_fontgen` at [ps2ui.py](repo:packages/baker/ps2ui_bake/ps2ui.py#L370).

### Options

```sh
ps2ui fontgen --help
```

```
usage: ps2ui fontgen [-h] [-o OUT_DIR] regular bold

positional arguments:
  regular               the regular-weight TTF
  bold                  the bold TTF

options:
  -h, --help            show this help message and exit
  -o OUT_DIR, --out-dir OUT_DIR
                        where to write them (default: fonts/)
```

| flag | argument | default | effect |
|---|---|---|---|
| (1st) | `<regular>` | required | measured with family `default` and weight `400` |
| (2nd) | `<bold>` | required | measured with family `default` and weight `700` |
| `-o`, `--out-dir` | `DIR` | `fonts` | directory for all three files; created if absent |

The wrapper fixes the family name to `default` and the weights to 400 and 700. Use the bare tool for another family name, another weight, or a custom charset.

### Output

Each face is the bare tool's metrics object with `family` set to `default`. The manifest names the two metrics files relative to itself and the TTFs by absolute path:

```sh
cat out/fonts.json
```

```
{
  "regular": { "ttf": ["/home/user/OPHTML/fonts/vendor/DejaVuSans.ttf"], "metrics": "default.metrics.json" },
  "bold":    { "ttf": ["/home/user/OPHTML/fonts/vendor/DejaVuSans-Bold.ttf"], "metrics": "default-bold.metrics.json" }
}
```

Each `ttf` value is a list of candidate paths, and the first that exists wins. Add more candidates by hand when the project must build on machines with fonts in different places, as [fonts/fonts.json](repo:fonts/fonts.json) does. The project file points at this manifest through its `fonts` key, described on [The project file](page:authoring/project-file#reference-table).

### Exit codes

| code | triggered by | fix |
|---|---|---|
| 0 | both faces and the manifest written | none |
| 2 | the bare tool refused for the first face | as for the bare tool |
| 1 | an uncaught error in the bare tool | as for the bare tool |
| 2 | a missing positional argument (argparse usage error) | pass both TTF paths |

The wrapper stops at the first non-zero return and writes no manifest. It creates `--out-dir` before the first face runs, so a refused run leaves an empty directory.

### Files written

| file | content |
|---|---|
| `DIR/default.metrics.json` | the regular face, weight 400 |
| `DIR/default-bold.metrics.json` | the bold face, weight 700 |
| `DIR/fonts.json` | the manifest: absolute TTF paths and the two metrics file names |

## Related pages

| page | why |
|---|---|
| [Text and fonts](page:authoring/text-and-fonts#behaviour) | how the compiler and baker consume advances, kerning and the charset |
| [The project file](page:authoring/project-file#reference-table) | the `fonts` key that names the manifest |
| [Installation](page:getting-started/installation#limits-and-errors) | installing both packages, and the 0.8.0 Raqm refusal |
| [ps2ui](page:cli/ps2ui#from-a-checkout) | the umbrella command and the checkout spelling |
