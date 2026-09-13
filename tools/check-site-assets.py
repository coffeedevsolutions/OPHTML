#!/usr/bin/env python3
"""Re-render every checked screenshot in docs/site and diff the bytes.

WHY THIS EXISTS. docs/site/assets/ holds the PNGs the documentation
pages embed, and docs/site/assets/assets.json records, for each one,
the command that produced it. A screenshot is a figure like any other
in this repository: true on the day it was rendered and unfalsifiable
after, unless something re-derives it. check-example-figures.py closed
that gap for the numbers in the example READMEs; this closes it for
the pictures. A previewer change that moves a glyph by one pixel, or
an example edit that recolours a panel, turns every committed render
into a picture of a tool that no longer exists, and nothing else in
the tree would say so.

WHAT IT CHECKS. Each manifest entry with `checked: true` has its
`command` run from the repository root with `OUT` replaced by a path
in a temporary directory, and the bytes it wrote are compared with the
committed file. `checked: false` entries are listed and skipped: they
are Playwright captures of the `ps2ui serve` page chrome, whose text
rendering is not byte-stable across browser versions, and the command
is kept only so the capture can be redone by hand.

WHAT THIS DOES NOT VOUCH FOR. That the example blobs the commands read
are current. The commands bake from examples/*/build/, which is
gitignored and exists only because a build.sh ran; a stale local build
with a matching PNG passes. In CI the step before this one builds the
examples, so it cannot happen there. On a workstation, rebuild before
trusting a pass. A missing committed file, a missing blob, a command
that exits non-zero, or a command that writes nothing at OUT is a
failure rather than a skip, for the reason check-example-figures.py
gives: a checker that passes when its subject is absent reports green
for the one state in which it has verified nothing.

Output is TAP: one `ok` / `not ok` line per entry, a `1..N` plan, and
exit 1 on any failure.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "docs", "site", "assets", "assets.json")


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        entries = json.load(fh)
    if not isinstance(entries, list):
        raise SystemExit("check-site-assets: %s is not a JSON list"
                         % os.path.relpath(MANIFEST, ROOT))
    for i, e in enumerate(entries):
        for key in ("path", "page", "command", "checked"):
            if key not in e:
                raise SystemExit("check-site-assets: entry %d (%s) has no "
                                 "`%s` field" % (i, e.get("path", "?"), key))
    return entries


def render(entry, tmpdir):
    """Run the entry's command with OUT substituted. Returns
    (out_path, failure_or_None)."""
    out = os.path.join(tmpdir, os.path.basename(entry["path"]))
    if "OUT" not in entry["command"]:
        return out, "command has no OUT placeholder"
    cmd = entry["command"].replace("OUT", out)
    proc = subprocess.run(cmd, shell=True, cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True)
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-3:]
        return out, ("command exited %d: %s"
                     % (proc.returncode, " | ".join(tail) or "(no stderr)"))
    if not os.path.exists(out):
        return out, "command exited 0 but wrote nothing at OUT"
    return out, None


def check(entry, tmpdir):
    """One TAP verdict: (ok, description)."""
    rel = entry["path"]
    committed = os.path.join(ROOT, "docs", "site", rel)
    if not os.path.exists(committed):
        return False, "%s: not in the tree (the manifest names it)" % rel
    if not entry["checked"]:
        return True, "%s # SKIP checked: false; redo by hand with the " \
                     "recorded command" % rel
    out, failure = render(entry, tmpdir)
    if failure:
        return False, "%s: %s" % (rel, failure)
    with open(committed, "rb") as a, open(out, "rb") as b:
        want, got = a.read(), b.read()
    if want != got:
        return False, ("%s: rendered %d bytes, committed %d bytes, and they "
                       "differ. Re-run the command from the manifest and "
                       "commit the result, or fix what moved."
                       % (rel, len(got), len(want)))
    return True, "%s (%d bytes)" % (rel, len(want))


def main():
    entries = load_manifest()
    print("1..%d" % len(entries))
    fail = 0
    tmpdir = tempfile.mkdtemp(prefix="site-assets-")
    try:
        for n, entry in enumerate(entries, 1):
            sub = os.path.join(tmpdir, str(n))
            os.makedirs(sub)
            ok, desc = check(entry, sub)
            print("%s %d - %s" % ("ok" if ok else "not ok", n, desc))
            if not ok:
                fail += 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if fail:
        print("# %d of %d assets failed" % (fail, len(entries)))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
