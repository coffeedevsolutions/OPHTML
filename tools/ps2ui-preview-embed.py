#!/usr/bin/env python3
"""Inline a ps2ui build into a standalone copy of ps2ui-preview.html.

The previewer normally reads a build directory off disk. That is the
right default locally and useless everywhere else: a reviewer looking at
a pull request, or anyone reading a CI run, has no checkout and no
toolchain. This writes one HTML file with the IR, the baked PNGs and any
referenced art carried inside it, so a preview travels as an artifact.

    python3 tools/ps2ui-preview-embed.py build/ -o preview.html

Reads the same directory ps2ui-dev writes: ui.json (required),
preview.png, states.png, plus whatever the IR's image commands point at.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys


def data_url(path):
    if not path or not os.path.isfile(path):
        return None
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode("ascii")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ps2ui-preview-embed")
    ap.add_argument("build", help="build directory (as written by ps2ui-dev -o)")
    ap.add_argument("-o", "--out", required=True, help="output .html path")
    ap.add_argument("--name", default=None,
                    help="label shown in the previewer status line")
    ap.add_argument("--template", default=None,
                    help="ps2ui-preview.html to embed into "
                         "(default: alongside this script)")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    template = args.template or os.path.join(here, "ps2ui-preview.html")
    ir_path = os.path.join(args.build, "ui.json")
    if not os.path.isfile(ir_path):
        print(f"no ui.json in {args.build}", file=sys.stderr)
        return 1
    with open(ir_path) as fh:
        ir = json.load(fh)

    # Art is addressed by build-host absolute path in the IR and by
    # basename in the browser, so key it the way the page will ask.
    images = {}
    for cmd in ir.get("commands", []):
        if cmd.get("op") != "image" or not cmd.get("src"):
            continue
        key = os.path.basename(cmd["src"]).lower()
        if key in images:
            continue
        for candidate in (cmd["src"], os.path.join(args.build, key)):
            url = data_url(candidate)
            if url:
                images[key] = url
                break
        else:
            print(f"warning: no pixels for {key}", file=sys.stderr)

    payload = {
        "name": args.name or os.path.basename(os.path.abspath(args.build)),
        "ir": ir,
        "preview": data_url(os.path.join(args.build, "preview.png")),
        "states": data_url(os.path.join(args.build, "states.png")),
        "images": images,
    }
    if not payload["preview"]:
        print("warning: no preview.png — the page will fall back to the "
              "IR replay, which is not GS-accurate", file=sys.stderr)

    with open(template) as fh:
        html = fh.read()

    # </script> anywhere inside the JSON would close the tag early.
    blob = json.dumps(payload).replace("</", "<\\/")
    marker = "<script>\n\"use strict\";"
    if marker not in html:
        print("template does not look like ps2ui-preview.html", file=sys.stderr)
        return 1
    html = html.replace(
        marker,
        f"<script>window.PS2UI_EMBED={blob};</script>\n{marker}",
        1,
    )

    with open(args.out, "w") as fh:
        fh.write(html)
    kb = os.path.getsize(args.out) / 1024
    print(f"{args.out} — {kb:.0f} KB, {len(ir.get('commands', []))} commands, "
          f"{len(images)} image(s) embedded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
