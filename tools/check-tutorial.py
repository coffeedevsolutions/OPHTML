#!/usr/bin/env python3
"""Run docs/tutorial-uc3.md as a stranger would, and check what it says.

WHY THIS EXISTS. Phase 4's exit gate is "a stranger with npm, pip and a
TTF reproduces the example without cloning the repo", and a tutorial is
the only artifact that can be checked against it. A tutorial nobody
re-runs is a document that was true on the day it was written -- the
failure this repository has now closed for example figures, PLAN's
prose, the sweep table and every version claim in the tree. It would be
a strange place to stop.

So the document is the source and this executes it: every ```sh block
in order, in one scratch directory, with `sh -e`. A ```text block
immediately after a command block is its expected output, and every
non-empty line of it must appear in what actually happened.

WHAT THIS PROVES AND WHAT IT DOES NOT. It proves the commands run in
the order given, from an empty directory, and produce the numbers
printed. It does NOT prove they work from an npm and pip install --
nothing is published, so the CLI names resolve through shims onto the
checkout. That gap is the exit gate itself, it is stated in the
tutorial's own last section, and it is the reason the shims are written
here rather than hidden: the day the packages go up, deleting this
function is the whole change.

The TTFs come from fonts/fonts.json, so the tutorial exercises the
"bring your own font" path against a real file rather than a fixture.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "tutorial-uc3.md")

# ```sh ... ``` followed optionally by ```text ... ```
BLOCK = re.compile(r"```sh\n(.*?)```(?:\s*\n```text\n(.*?)```)?", re.S)

SHIMS = {
    "ps2ui-layout": 'exec node "%s/packages/layout/bin/ps2ui-layout.js" "$@"',
    "ps2ui-dev": 'exec node "%s/packages/layout/bin/ps2ui-dev.js" "$@"',
    "ps2ui-bake": 'PYTHONPATH="%s/packages/baker" exec python3 -m ps2ui_bake "$@"',
    "ps2ui-check":
        'PYTHONPATH="%s/packages/baker" exec python3 -m ps2ui_bake.check "$@"',
    "ps2ui-fontgen":
        'PYTHONPATH="%s/packages/baker" exec python3 -m ps2ui_bake.fontgen "$@"',
}


def shim_dir(tmp):
    """The five console scripts, forwarding to this checkout.

    Written from the table in the tutorial's own last section, so the
    document tells the reader exactly what CI substitutes.
    """
    d = os.path.join(tmp, "bin")
    os.makedirs(d)
    for name, body in SHIMS.items():
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\n" + (body % ROOT) + "\n")
        os.chmod(path, 0o755)
    return d


def ttfs():
    """Real TTF paths from the repository's manifest, first that exists."""
    import json
    with open(os.path.join(ROOT, "fonts", "fonts.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    out = {}
    for face, var in (("regular", "TTF_REGULAR"), ("bold", "TTF_BOLD")):
        for cand in manifest[face]["ttf"]:
            if os.path.exists(cand):
                out[var] = cand
                break
        else:
            raise SystemExit("not ok - check-tutorial: no TTF on this "
                             "machine for '%s'; the tutorial's whole "
                             "premise is a person with a font file"
                             % face)
    return out


def blocks():
    text = open(DOC, encoding="utf-8").read()
    found = [(m.group(1), m.group(2)) for m in BLOCK.finditer(text)]
    if not found:
        raise SystemExit("not ok - docs/tutorial-uc3.md has no ```sh blocks. "
                         "They were reformatted, and this check has stopped "
                         "running the tutorial rather than started passing "
                         "it.")
    return found


def main():
    cmds = blocks()
    expected = sum(1 for _, out in cmds if out)
    if not expected:
        raise SystemExit("not ok - no ```sh block in the tutorial is "
                         "followed by a ```text block, so nothing about the "
                         "output is asserted and this would pass on any "
                         "commands that merely exit 0")

    tmp = tempfile.mkdtemp(prefix="ps2ui-tutorial-")
    env = dict(os.environ)
    env["PATH"] = shim_dir(tmp) + os.pathsep + env["PATH"]
    env.update(ttfs())
    # One shell for the whole document: `cd browser` in step 1 has to
    # still be in effect at step 5, exactly as it is for a reader.
    script, checks = [], []
    for i, (cmd, want) in enumerate(cmds):
        script.append(cmd)
        checks.append((i, cmd, want))
    work = os.path.join(tmp, "work")
    os.makedirs(work)

    fail = []
    log = []
    for i, cmd, want in checks:
        marker = "___ps2ui_block_%d___" % i
        run = "\n".join(script[:i + 1] + ['echo "%s"' % marker])
        proc = subprocess.run(["sh", "-e", "-c", run], cwd=work, env=env,
                              capture_output=True, text=True)
        got = proc.stdout + proc.stderr
        if proc.returncode != 0:
            fail.append("block %d exited %d:\n    $ %s\n    %s"
                        % (i + 1, proc.returncode, cmd.strip().splitlines()[0],
                           got.strip().splitlines()[-1] if got.strip() else ""))
            break
        if want:
            missing = [ln for ln in want.splitlines()
                       if ln.strip() and ln not in got]
            if missing:
                fail.append("block %d ran, but the tutorial's output block "
                            "claims lines that did not appear:\n%s"
                            % (i + 1, "\n".join("    " + m for m in missing)))
            else:
                log.append("ok - tutorial block %d: %d output line(s) as "
                           "documented" % (i + 1, len(want.strip().splitlines())))
        else:
            log.append("ok - tutorial block %d ran clean" % (i + 1))

    for line in log:
        print(line)
    for f in fail:
        print("not ok - %s" % f)
    if not fail:
        print("ok - docs/tutorial-uc3.md: %d block(s), %d with asserted "
              "output, from an empty directory" % (len(cmds), expected))
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("# scratch kept at %s" % tmp)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
