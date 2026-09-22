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
printed. It does NOT prove they work from an npm and pip install: the
CLI names resolve through shims onto the checkout, which is what makes
this a check of THIS tree rather than of whatever is on the registries.
Both packages are published as of 0.3.0, and deleting these shims is
still not the change that closes the gap -- it would point this job at
the last published version instead of the tree under test. Closing it
means a SEPARATE job that installs from the registries and runs this
document, on more than one platform: the first real attempt at the exit
gate failed on macOS, where pip's Pillow wheel has no Raqm, and this
job on ubuntu could never have seen it.

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
# Two documents carry the same eight steps: the repository tutorial
# and the site's port of it, whose asserted output blocks are kept
# byte-identical so this one check covers both. Each runs from its own
# empty directory and is held to ASSERTED_BLOCKS on its own.
DOCS = [os.path.join(ROOT, "docs", "tutorial-uc3.md"),
        os.path.join(ROOT, "docs", "site", "getting-started",
                     "tutorial-game-browser.md")]

# ```sh ... ``` followed optionally by ```text ... ```
BLOCK = re.compile(r"```sh\n(.*?)```(?:\s*\n```text\n(.*?)```)?", re.S)

# WHICH command blocks carry an asserted output block, by 1-based
# position in the document. Named here rather than counted from the
# file, because a floor is not a fence.
#
# The first version only refused a document with ZERO ```text blocks.
# Deleting three of the four passed, reporting "1 with asserted
# output" on the summary line -- a number that reveals the erosion,
# PRINTED rather than checked, which is the shape of #87's `79` and
# exactly what this project keeps catching. At 1-of-7 the tutorial is
# most of the way back to "commands that merely exit 0", the state the
# guard exists to prevent.
#
# An exact SET, not a count: moving an assertion from the bake to the
# fontgen keeps the count and changes what is covered. Lowering this
# is now an edit to a check, which is the friction it should have.
ASSERTED_BLOCKS = {1, 5, 6, 7}

SHIMS = {
    "ps2ui": 'PYTHONPATH="%s/packages/baker" exec python3 -m ps2ui_bake.ps2ui "$@"',
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
    """Real TTF paths from the repository's manifest, via the resolver.

    THE THIRD READER OF fonts.json, AND IT USED TO BE THE ODD ONE OUT.
    This walked `manifest[face]["ttf"]` with a bare os.path.exists and
    no expanduser -- so `~/Library/Fonts/DejaVuSans.ttf`, which is in
    that manifest and is where macOS puts a font a person installs for
    themselves, resolved for `load_font_manifest` and not for this.
    Same file, same machine, two answers:

        load_font_manifest()  -> /root/Library/Fonts/DejaVuSans.ttf
        this function         -> "no TTF on this machine"

    That is the finding this repository has now had three times -- two
    lists for one job, and the one that is not the product's is the one
    that is wrong -- and it mattered here because the macOS arm of
    registry.yml installs its font with `brew install --cask
    font-dejavu`, which is a per-user install landing in exactly that
    directory. The arm would have gone red weekly for a reason that is
    not the release's fault, which is how a scheduled job earns being
    ignored.

    So it calls the resolver the baker calls. A candidate added for a
    user is added for this in the same edit, and there is no third
    spelling of "first one that exists".
    """
    sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))
    from ps2ui_bake.cli import load_font_manifest
    try:
        manifest = load_font_manifest(os.path.join(ROOT, "fonts", "fonts.json"))
    except FileNotFoundError as exc:
        raise SystemExit("not ok - check-tutorial: %s. The tutorial's whole "
                         "premise is a person with a font file; fonts.json "
                         "lists the paths that are looked in." % exc)
    return {"TTF_REGULAR": manifest["regular"]["ttf"],
            "TTF_BOLD": manifest["bold"]["ttf"]}


def blocks(doc):
    text = open(doc, encoding="utf-8").read()
    found = [(m.group(1), m.group(2)) for m in BLOCK.finditer(text)]
    if not found:
        raise SystemExit("not ok - %s has no ```sh blocks. "
                         % os.path.relpath(doc, ROOT) +
                         "They were reformatted, and this check has stopped "
                         "running the tutorial rather than started passing "
                         "it.")
    return found


def selftest():
    """Check what this script SAYS when a block fails.

    WHY A SELF-TEST AND NOT A FENCE. Every other guard in tools/ is
    falsifiable with tools/falsify.sh: break the thing, watch the check
    go red. That does not reach here, because this defect lives on the
    FAILURE path and CI only ever exercises the success one. A tutorial
    that passes prints no report at all, so reverting `tail()` to
    `splitlines()[-1]` would keep every job in this repository green
    while deleting the diagnosis again -- which is how it survived in
    the first place, and precisely the shape of "a check that passes for
    the wrong reason" that docs/method.md is about.

    So the failure path is run on purpose, against blocks written to
    fail, and the REPORT is the thing asserted. Synthetic commands
    rather than a real tutorial: the subject is the reporting, and
    borrowing a real failure would couple this to whatever the tutorial
    happens to be doing wrong that week.
    """
    fails = []

    def report(cmds):
        work = tempfile.mkdtemp(prefix="ps2ui-selftest-")
        shutil.rmtree(work)
        out, log = [], []
        try:
            run_doc(DOCS[0], cmds, len(cmds), work, dict(os.environ), out, log)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return "\n".join(out)

    # 1. A failing block shows every line it printed, not the last one.
    #    The three `error:` lines are the CSS stage's shape, which is
    #    the case that made this worth fixing.
    r = report([("printf 'error: one\\nerror: two\\nerror: three\\n'; exit 1", "")])
    for want in ("error: one", "error: two", "error: three"):
        if want not in r:
            fails.append("a failing block dropped %r from its report" % want)

    # 2. A block that RAN but printed something else shows what it
    #    printed. Half a comparison is what made a path separator on
    #    Windows invisible in its own log.
    r = report([("printf 'out -> fonts\\\\x.json\\n'", "out -> fonts/x.json")])
    if "fonts\\x.json" not in r:
        fails.append("a mismatched block did not show what it printed")
    if "out -> fonts/x.json" not in r:
        fails.append("a mismatched block stopped naming what was expected")

    # 3. Dropped lines are counted. A silently clipped tail is the
    #    original defect one size up.
    r = report([("for n in $(seq 1 %d); do echo L$n; done; exit 1"
                 % (TAIL_LINES + 5), "")])
    if "5 earlier line(s) omitted" not in r:
        fails.append("a clipped tail did not say how much it dropped")
    if "L%d" % (TAIL_LINES + 5) not in r:
        fails.append("a clipped tail dropped the END rather than the start")

    # 4. Silence is named. "It failed and said nothing" points at the
    #    command; a blank line points at nothing.
    if "(no output)" not in report([("exit 1", "")]):
        fails.append("a silent failure did not say it was silent")

    # 5. The harness's own sentinel stays out of the report.
    if "___ps2ui_block_" in report([("printf 'x\\n'", "not-this-line")]):
        fails.append("the block marker leaked into a report")

    for f in fails:
        print("not ok - check-tutorial selftest: %s" % f)
    if fails:
        return 1
    print("ok - check-tutorial selftest: a failing block reports every line "
          "it printed, a mismatch reports both sides, a clipped tail counts "
          "what it dropped, silence is named, and the marker is dropped")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    docs = {}
    for doc in DOCS:
        cmds = blocks(doc)
        asserted = {i + 1 for i, (_, out) in enumerate(cmds) if out}
        if asserted != ASSERTED_BLOCKS:
            lost = sorted(ASSERTED_BLOCKS - asserted)
            gained = sorted(asserted - ASSERTED_BLOCKS)
            raise SystemExit(
                "not ok - %s: the asserted-output blocks are %s; this "
                "check expects %s.%s%s\n  Every ```sh block listed in "
                "ASSERTED_BLOCKS must be followed by a ```text block. A "
                "tutorial that only checks exit statuses is the thing the "
                "check exists to prevent, and it gets there one deleted "
                "block at a time."
                % (os.path.relpath(doc, ROOT), sorted(asserted) or "none",
                   sorted(ASSERTED_BLOCKS),
                   "\n  Lost: %s -- output no longer checked." % lost if lost
                   else "",
                   "\n  Gained: %s -- add it to ASSERTED_BLOCKS." % gained
                   if gained else ""))
        docs[doc] = (cmds, len(asserted))

    # --from-registry: DO NOT SHIM. The commands then resolve to
    # whatever `pip install ophtml` and `npm install -g @ophtml/layout`
    # put on PATH, which is a different subject from the default run
    # and not a replacement for it. The default run tests THIS TREE;
    # this one tests THE RELEASE, and can only ever test the last
    # published version, so it belongs on a schedule rather than on a
    # push. See .github/workflows/registry.yml.
    #
    # WHAT IT STILL DOES NOT PROVE. The tutorial text and this script
    # come from a checkout, because they have to come from somewhere;
    # only the COMMANDS come from the registries. The exit gate says
    # "without cloning this repository" and this is the closest an
    # automated run gets to it. Stated rather than implied, because a
    # green run here is going to be read as the gate.
    # UNKNOWN ARGUMENTS ARE REFUSED, the same way and for the same
    # reason as check-versions.py's.
    #
    # `--from-registry` selects which of two SUBJECTS this runs
    # against: the checkout, or the release. A mistyped or renamed flag
    # was silently ignored, so `--from-registery` ran the shimmed
    # tutorial and printed the same green line -- registry.yml would
    # then have reported the release healthy having tested the tree,
    # which is the exact swap that file's header says must not be
    # possible. The only visible difference was a `#` line in a log.
    for a in argv:
        if a not in ("--from-registry", "--selftest"):
            raise SystemExit(
                "not ok - check-tutorial: unknown argument %r. The flags "
                "are --from-registry, which changes what this runs "
                "against (installed packages rather than shims onto this "
                "checkout -- different subjects, so a flag that does not "
                "parse must not quietly pick one), and --selftest, which "
                "runs no tutorial and checks this script's own failure "
                "reporting." % a)
    if "--selftest" in argv:
        return selftest()
    from_registry = "--from-registry" in argv
    tmp = tempfile.mkdtemp(prefix="ps2ui-tutorial-")
    env = dict(os.environ)
    if not from_registry:
        env["PATH"] = shim_dir(tmp) + os.pathsep + env["PATH"]
    else:
        missing = [c for c in SHIMS if shutil.which(c) is None]
        if missing:
            raise SystemExit(
                "not ok - --from-registry, but %s not on PATH. This mode "
                "runs the tutorial against installed packages; install "
                "them first (pip install ophtml; npm install -g "
                "@ophtml/layout) or drop the flag to run against the "
                "checkout." % ", ".join(sorted(missing)))
        print("# --from-registry: %s" % ", ".join(
            "%s -> %s" % (c, shutil.which(c)) for c in sorted(SHIMS)))
    env.update(ttfs())
    fail = []
    log = []
    for n, (doc, (cmds, expected)) in enumerate(docs.items()):
        run_doc(doc, cmds, expected, os.path.join(tmp, "work%d" % n), env,
                fail, log)

    for line in log:
        print(line)
    for f in fail:
        print("not ok - %s" % f)
    if not fail:
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("# scratch kept at %s" % tmp)
    return 1 if fail else 0


# How many lines of a failing block's output to print. Twenty carries a
# compiler's error list -- the CSS stage reports every error in a sheet
# now, one line each -- without turning a failure into a wall.
TAIL_LINES = 20


def tail(got, marker=None, limit=TAIL_LINES):
    """The end of a failing block's output, indented and bounded.

    THIS REPLACES `splitlines()[-1]`, WHICH THREW THE DIAGNOSIS AWAY.
    On a failing `ps2ui build` the last line is `ps2ui: ps2ui-layout
    failed on ui/library.html (exit 1)` -- the wrapper's own summary --
    and everything the compiler said above it was captured and dropped.
    `ps2ui.py` runs the compiler with stderr inheriting under the
    comment "The compiler already printed why, in its own words. Adding
    a second summary here would bury it", and then this function buried
    it, keeping exactly the summary that file declined to add. Two
    places each locally right, combining to delete the evidence. It cost
    a Windows failure that could not be diagnosed from its own log.

    A TAIL RATHER THAN EVERYTHING, because `run` re-executes blocks 1..i
    in one shell, so `got` carries every earlier block's output as well:
    dumping all of it on block 8 buries the failure in seven blocks of
    healthy chatter, which is the same defect pointing the other way.
    The failure is always at the end, so the end is what is kept.

    AND THE OMISSION IS COUNTED. A tail that silently drops lines is the
    original defect one size up -- a reader cannot tell a complete
    message from a clipped one -- so when lines go, the line saying so
    goes in their place.

    EMPTY IS NAMED RATHER THAN PRINTED BLANK. "It failed and said
    nothing" is a finding: it points at the command rather than at its
    message. A blank line reads as a formatting slip.

    THE BLOCK MARKER IS DROPPED. `run` appends `echo ___ps2ui_block_N___`
    to know the block reached its end, so on a block that RAN the
    sentinel is the last thing printed -- and printing the harness's own
    bookkeeping back at a reader looking for their error is noise from
    the tool that is supposed to be helping.
    """
    lines = [ln for ln in got.strip().splitlines()
             if marker is None or ln.strip() != marker]
    if not lines:
        return "    (no output)"
    shown = lines[-limit:]
    dropped = len(lines) - len(shown)
    out = ["    " + ln for ln in shown]
    if dropped:
        out.insert(0, "    ... %d earlier line(s) omitted" % dropped)
    return "\n".join(out)


def run_doc(doc, cmds, expected, work, env, fail, log):
    name = os.path.relpath(doc, ROOT)
    # One shell for the whole document: `cd browser` in step 1 has to
    # still be in effect at step 5, exactly as it is for a reader.
    script, checks = [], []
    for i, (cmd, want) in enumerate(cmds):
        script.append(cmd)
        checks.append((i, cmd, want))
    os.makedirs(work)

    for i, cmd, want in checks:
        marker = "___ps2ui_block_%d___" % i
        run = "\n".join(script[:i + 1] + ['echo "%s"' % marker])
        proc = subprocess.run(["sh", "-e", "-c", run], cwd=work, env=env,
                              capture_output=True, text=True)
        got = proc.stdout + proc.stderr
        if proc.returncode != 0:
            fail.append("%s block %d exited %d:\n    $ %s\n%s"
                        % (name, i + 1, proc.returncode,
                           cmd.strip().splitlines()[0], tail(got, marker)))
            return
        if want:
            missing = [ln for ln in want.splitlines()
                       if ln.strip() and ln not in got]
            if missing:
                # THE OBSERVATION BESIDE THE CLAIM. Listing what the
                # document promised and not what the command printed
                # states half a comparison: a reader who can see both
                # spots `fonts\default.metrics.json` against
                # `fonts/default.metrics.json` in a glance, and a reader
                # who can see only the expected line has to go and run
                # it themselves to find out it was a separator.
                fail.append("%s block %d ran, but the tutorial's output "
                            "block claims lines that did not appear:\n%s\n"
                            "  and what it printed instead:\n%s"
                            % (name, i + 1,
                               "\n".join("    " + m for m in missing),
                               tail(got, marker)))
            else:
                log.append("ok - %s block %d: %d output line(s) as "
                           "documented"
                           % (name, i + 1, len(want.strip().splitlines())))
        else:
            log.append("ok - %s block %d ran clean" % (name, i + 1))
    log.append("ok - %s: %d block(s), %d of %d asserted as expected, from "
               "an empty directory"
               % (name, len(cmds), expected, len(ASSERTED_BLOCKS)))


if __name__ == "__main__":
    sys.exit(main())
