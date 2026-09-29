#!/usr/bin/env python3
"""Hold the container images CI builds in, and the one variable a
workflow input reaches a shell through, to what this tree decided.

WHY THIS EXISTS. Two defects found by auditing this repository for what
a stranger could exploit, and both are the shape this project keeps
finding: a decision that is correct in the file and unguarded, so the
next edit reverses it silently and every check stays green.

  * THE RELEASE CONTAINER. `console-release.yml` builds `ophtml.elf`
    and attaches it to a GitHub Release, which is the only way a
    stranger gets the launcher without a clone. It ran in
    `ghcr.io/ps2dev/ps2dev:latest`, so the compiler for a tagged
    release was whatever ghcr.io served the minute the tag was pushed,
    nothing downstream re-verifies the ELF -- no emulator gate runs on
    it, and the `SHA256SUMS` beside it is computed by the same job that
    built it -- and the release cannot be rebuilt from the tag
    afterwards. It is pinned by digest now.

    `hw.yml` uses the same image and MUST NOT be pinned. Its TFX probe
    exists to notice gsKit changing upstream, so freezing the container
    would freeze the watch. That is why this checker asserts the two
    directions separately rather than "every container is pinned": a
    rule of that shape would be satisfied by pinning hw.yml, which is
    the one change here that quietly deletes a watch.

  * FUZZ_TIME. `fuzz.yml`'s `workflow_dispatch` takes a free-text
    `seconds`, hands it to `make -C runtime fuzz FUZZ_TIME=...`, and
    `runtime/Makefile` substituted it unquoted into the libFuzzer
    command line. `seconds: 1; touch <file>` created the file, in a
    workflow holding `actions: write`. Firing it needs push access, so
    it was a footgun and not an escalation -- but the same Makefile
    line is what any future caller would use.

    runtime/Makefile validates FUZZ_TIME as a whole number at parse
    time with pure make text functions, and quotes it. The last check
    below RUNS that guard rather than reading it, because a guard whose
    presence is grepped for is a guard nobody has executed.

    FUZZ_ARGS is the same variable shape with the opposite decision:
    it is word-split on purpose, so it reaches the shell as text and
    cannot be quoted without breaking `-seed=1`. It is safe only
    because nothing outside this repository sets it, and that is the
    part a checker can hold: a workflow may pass FUZZ_ARGS a literal
    and may not pass it one of its own inputs.

  * THE DRAFT GATE on `console-release.yml`'s `attach` job. The gate
    used to be a side effect of the create path: the script asked only
    "does a release exist", which is also what a release a person
    PUBLISHED looks like, so that case fell through to
    `gh release upload --clobber` against a live public download with no
    gate at all. It now reads `isDraft` and refuses a published release
    unless the dispatch says `replace_published: true`.

    A three-state gate written in shell inside a YAML block is the kind
    of thing nothing ever runs until the day it matters. So this checker
    EXTRACTS that script and EXECUTES it, against a stub `gh` on PATH,
    in all four combinations of release state and the input -- which is
    the same reason the FUZZ_TIME guard below is run rather than
    grepped, and the same reason that one's first version passed with
    the guard deleted.

Run by ci.yml. Exits 0 with one `ok -` line per check, or 1 naming
every failure.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The image both jobs build in, and the opposite thing each wants from
# it. (workflow, job) -> "digest" or "floating".
CONTAINER_POLICY = {
    (".github/workflows/console-release.yml", "elf"): "digest",
    (".github/workflows/hw.yml", "elf"): "floating",
}
FLOATING_TAG = "ghcr.io/ps2dev/ps2dev:latest"
DIGEST_RE = re.compile(r"^ghcr\.io/ps2dev/ps2dev@sha256:[0-9a-f]{64}$")

WORKFLOW_DIR = os.path.join(ROOT, ".github", "workflows")

problems = []
oks = []


def check(ok, ok_msg, bad_msg):
    if ok:
        oks.append(ok_msg)
    else:
        problems.append(bad_msg)


def containers():
    """Every `container:` in every workflow, as (workflow, job, image).

    Line-based on purpose: no YAML library is a dependency of anything
    else in this tree, and the shape being read is two fixed indents
    under `jobs:`.
    """
    found = []
    for name in sorted(os.listdir(WORKFLOW_DIR)):
        if not name.endswith((".yml", ".yaml")):
            continue
        rel = ".github/workflows/" + name
        job = None
        in_jobs = False
        with open(os.path.join(WORKFLOW_DIR, name), encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if re.match(r"^jobs:\s*$", line):
                    in_jobs = True
                    continue
                if not in_jobs:
                    continue
                if re.match(r"^\S", line):          # back out to top level
                    in_jobs = False
                    continue
                m = re.match(r"^  ([A-Za-z_][\w-]*):\s*$", line)
                if m:
                    job = m.group(1)
                    continue
                m = re.match(r"^    container:\s*(\S+)\s*$", line)
                if m:
                    found.append((rel, job, m.group(1)))
    return found


# 1. EVERY CONTAINER IS A DECISION THIS FILE HAS MADE. A new job that
#    runs in an image nobody chose a policy for fails here rather than
#    inheriting whichever neighbour it was copied from.
seen = containers()
unknown = [(w, j, i) for (w, j, i) in seen if (w, j) not in CONTAINER_POLICY]
check(not unknown,
      "every workflow container has a policy in this file (%d)" % len(seen),
      "these jobs run in a container with no policy in "
      "tools/check-workflow-pins.py, so nothing says whether it should be "
      "pinned: %s. Add it to CONTAINER_POLICY with the reason."
      % ", ".join("%s job `%s` -> %s" % t for t in unknown))

for (wf, job), policy in sorted(CONTAINER_POLICY.items()):
    images = [i for (w, j, i) in seen if (w, j) == (wf, job)]
    if len(images) != 1:
        problems.append(
            "%s has %d `container:` line(s) in job `%s`, expected 1. This "
            "checker's policy for it is `%s`; if the job was renamed or "
            "removed, move the policy with it." % (wf, len(images), job, policy))
        continue
    image = images[0]

    # 2. THE RELEASE PATH IS PINNED BY DIGEST. Its output is a public
    #    download nothing downstream re-verifies.
    if policy == "digest":
        check(DIGEST_RE.match(image) is not None,
              "%s job `%s` is pinned by digest" % (wf, job),
              "%s job `%s` runs in `%s`. This job builds the ELF attached to "
              "a GitHub Release, so it must name an immutable digest "
              "(ghcr.io/ps2dev/ps2dev@sha256:<64 hex>): nothing re-verifies "
              "the released binary, and its SHA256SUMS is written by this "
              "same job. Re-resolve the tag and pin the new digest rather "
              "than reverting to a tag." % (wf, job, image))

    # 3. THE DRIFT WATCH IS NOT PINNED, and this direction is the one a
    #    well-meaning "pin everything" change breaks.
    if policy == "floating":
        check(image == FLOATING_TAG,
              "%s job `%s` still floats on %s" % (wf, job, FLOATING_TAG),
              "%s job `%s` runs in `%s`, not `%s`. This job's TFX probe "
              "exists to notice gsKit changing upstream; pinning the image "
              "freezes the watch without failing anything, which is the one "
              "way to delete a check here silently. If the image really must "
              "move, say what watches gsKit instead."
              % (wf, job, image, FLOATING_TAG))

# 4. FUZZ_ARGS TAKES LITERALS ONLY. It is word-split by design, so a
#    workflow input routed into it lands in a shell as text.
bad_args = []
for name in sorted(os.listdir(WORKFLOW_DIR)):
    if not name.endswith((".yml", ".yaml")):
        continue
    rel = ".github/workflows/" + name
    with open(os.path.join(WORKFLOW_DIR, name), encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            for m in re.finditer(r"FUZZ_ARGS=(\S*)", line):
                val = m.group(1)
                if "${{" in val or "$" in val:
                    bad_args.append("%s:%d passes FUZZ_ARGS=%s" % (rel, n, val))
check(not bad_args,
      "no workflow routes an expression into FUZZ_ARGS",
      "FUZZ_ARGS reaches /bin/sh unquoted on purpose (runtime/Makefile says "
      "why), so it may carry literals only: %s. Validate the value and pass "
      "it through FUZZ_TIME's shape instead, or quote it in the Makefile and "
      "give up the word splitting." % "; ".join(bad_args))

# 5. THE DRAFT GATE IS EXECUTED. Extracted from the workflow and run
#    against a stub `gh`, because the alternative is asserting that a
#    three-state shell gate contains some strings.
ATTACH_STEP = "Attach to the tag's release, creating a draft if it has none"


def extract_run(workflow, step_name):
    """The `run:` block of one named step, dedented, or None.

    Line-based for the reason containers() is: no YAML library is a
    dependency of anything else in this tree, and a `run: |` block is
    two fixed indents and a scalar.
    """
    lines = open(os.path.join(ROOT, workflow), encoding="utf-8").read().split("\n")
    i = next((k for k, ln in enumerate(lines)
              if ln.strip() == "- name: " + step_name), None)
    if i is None:
        return None
    j = next((k for k in range(i + 1, len(lines))
              if lines[k].rstrip() == "        run: |"), None)
    if j is None:
        return None
    body = []
    for ln in lines[j + 1:]:
        if ln.strip() and not ln.startswith("          "):
            break
        body.append(ln)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(ln[10:] if ln.startswith("          ") else ln
                      for ln in body) + "\n"


GH_STUB = r"""#!/bin/bash
# A stub `gh`. Logs the argv it was given and answers from $STUB_STATE.
printf '%s\n' "$*" >> "$GH_LOG"
if [ "$1" = release ] && [ "$2" = view ]; then
    case " $* " in
        *" isDraft "*)
            case "$STUB_STATE" in
                missing)   exit 1 ;;
                draft)     echo true ;;
                published) echo false ;;
            esac ;;
        *) echo ophtml.elf ;;
    esac
    exit 0
fi
if [ "$1" = release ] && [ "$2" = download ]; then
    [ "$STUB_STATE" = missing ] && exit 1
    dir=""; prev=""
    for a in "$@"; do [ "$prev" = --dir ] && dir=$a; prev=$a; done
    mkdir -p "$dir"
    printf '%s\n' "$STUB_PREV_SUMS" > "$dir/SHA256SUMS"
    exit 0
fi
exit 0
"""

SCENARIOS = [
    # state,      replace_published, prev sums,  expect exit 0, expect create, expect upload, must say
    ("missing",   "false", "",          True,  True,  True,  "no SHA256SUMS"),
    ("draft",     "false", "same",      True,  False, True,  "rebuilt the same bytes"),
    ("draft",     "false", "different", True,  False, True,  "::warning::the checksums differ"),
    ("published", "false", "same",      False, False, False, "is PUBLISHED"),
    ("published", "true",  "same",      True,  False, True,  "::warning::v9.9.9 is published"),
]

script = extract_run(".github/workflows/console-release.yml", ATTACH_STEP)
if script is None:
    problems.append(
        ".github/workflows/console-release.yml has no `run: |` under a step "
        "named %r, so the draft gate cannot be extracted and nothing here "
        "runs it. If the step was renamed, rename ATTACH_STEP with it."
        % ATTACH_STEP)
else:
    OURS = "abc123  ophtml.elf\n"
    for state, replace, prev, want_ok, want_create, want_upload, must_say in SCENARIOS:
        label = "%s release, replace_published=%s%s" % (
            state, replace, "" if not prev else ", prev sums %s" % prev)
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "bin"))
            gh = os.path.join(tmp, "bin", "gh")
            with open(gh, "w", encoding="utf-8") as fh:
                fh.write(GH_STUB)
            os.chmod(gh, 0o755)
            os.makedirs(os.path.join(tmp, "dist"))
            with open(os.path.join(tmp, "dist", "SHA256SUMS"), "w",
                      encoding="utf-8") as fh:
                fh.write(OURS)
            sh = os.path.join(tmp, "attach.sh")
            with open(sh, "w", encoding="utf-8") as fh:
                fh.write(script)
            log = os.path.join(tmp, "gh.log")
            open(log, "w").close()
            env = dict(os.environ)
            env.update({
                "PATH": os.path.join(tmp, "bin") + os.pathsep + env["PATH"],
                "TAG": "v9.9.9",
                "REPLACE_PUBLISHED": replace,
                "RUNNER_TEMP": os.path.join(tmp, "rt"),
                "STUB_STATE": state,
                "STUB_PREV_SUMS": (OURS.strip() if prev == "same"
                                   else "999999  ophtml.elf"),
                "GH_LOG": log,
            })
            os.makedirs(env["RUNNER_TEMP"], exist_ok=True)
            run = subprocess.run(["bash", "-e", sh], cwd=tmp, env=env,
                                 capture_output=True, text=True)
            calls = open(log, encoding="utf-8").read()
            said = run.stdout + run.stderr
            got_create = "release create" in calls
            got_upload = "release upload" in calls
            wrong = []
            # A create must carry BOTH: --draft so this workflow never
            # publishes, and --verify-tag so a typo in the dispatch
            # input cannot mint a tag on main.
            if got_create:
                created = [ln for ln in calls.split("\n")
                           if "release create" in ln]
                for flag in ("--draft", "--verify-tag"):
                    if not any(flag in ln for ln in created):
                        wrong.append("created a release without %s" % flag)
            if (run.returncode == 0) != want_ok:
                wrong.append("exited %d, wanted %s"
                             % (run.returncode,
                                "0" if want_ok else "non-zero"))
            if got_create != want_create:
                wrong.append("%s a draft" % ("created" if got_create
                                             else "did not create"))
            if got_upload != want_upload:
                wrong.append("%s the files" % ("uploaded" if got_upload
                                               else "did not upload"))
            if must_say not in said:
                wrong.append("never said %r" % must_say)
            check(not wrong,
                  "the attach gate, run for real: %s" % label,
                  "the attach script, extracted from console-release.yml and "
                  "run against a stub gh for a %s: %s. THE PUBLISHED CASE IS "
                  "THE ONE THAT MATTERS -- uploading there replaces a "
                  "download people already have, under the same version "
                  "number.\n--- gh calls ---\n%s\n--- output ---\n%s"
                  % (label, "; ".join(wrong), calls, said[-2000:]))

# 6. THE CORPUS HEALTH CHECKS ARE EXECUTED TOO, and for the same
#    reason they exist: the thing they guard against is the nightly
#    fuzzer reporting half an hour of health while testing almost
#    nothing. A check written to catch that, which nobody ever runs, is
#    the same defect one level up.
#
#    An empty restored cache and a shrinking corpus are both states
#    that cannot be produced on demand in CI, so they are produced here.
CORPUS_DIR = os.path.join("runtime", "build", "fuzz-corpus")

CORPUS_SCENARIOS = [
    # step,             files, env,                          ok,    must say
    ("Say what the corpus arrived as", 3, {"CACHE_HIT": "true"},
     True,  "3 file(s)"),
    ("Say what the corpus arrived as", 0, {"CACHE_HIT": "true"},
     False, "::error::"),
    ("Say what the corpus arrived as", 0, {"CACHE_HIT": ""},
     True,  "::warning::no fuzz-corpus cache entry"),
    ("Say what the corpus arrived as", 2, {"CACHE_HIT": "false"},
     True,  "::warning::no fuzz-corpus cache entry"),
    ("The corpus did not shrink", 5, {"CORPUS_BEFORE_FILES": "3"},
     True,  "5 file(s)"),
    ("The corpus did not shrink", 3, {"CORPUS_BEFORE_FILES": "5"},
     False, "::error::the corpus lost files"),
]

for step_name, files, extra, want_ok, must_say in CORPUS_SCENARIOS:
    body = extract_run(".github/workflows/fuzz.yml", step_name)
    if body is None:
        problems.append(
            ".github/workflows/fuzz.yml has no `run: |` under a step named "
            "%r, so the corpus health check cannot be extracted and nothing "
            "here runs it." % step_name)
        continue
    label = "%s, %d file(s), %s" % (
        step_name, files,
        ", ".join("%s=%r" % kv for kv in sorted(extra.items())))
    with tempfile.TemporaryDirectory() as tmp:
        corpus = os.path.join(tmp, CORPUS_DIR)
        os.makedirs(corpus)
        for k in range(files):
            with open(os.path.join(corpus, "blob%d" % k), "wb") as fh:
                fh.write(b"\0" * 16)
        sh = os.path.join(tmp, "step.sh")
        with open(sh, "w", encoding="utf-8") as fh:
            fh.write(body)
        env = dict(os.environ)
        env.update(extra)
        env["GITHUB_ENV"] = os.path.join(tmp, "env")
        env["GITHUB_STEP_SUMMARY"] = os.path.join(tmp, "summary")
        open(env["GITHUB_ENV"], "w").close()
        open(env["GITHUB_STEP_SUMMARY"], "w").close()
        run = subprocess.run(["bash", "-e", sh], cwd=tmp, env=env,
                             capture_output=True, text=True)
        said = run.stdout + run.stderr
        wrong = []
        if (run.returncode == 0) != want_ok:
            wrong.append("exited %d, wanted %s"
                         % (run.returncode, "0" if want_ok else "non-zero"))
        if must_say not in said:
            wrong.append("never said %r" % must_say)
        check(not wrong,
              "corpus health, run for real: %s" % label,
              "the `%s` step, extracted from fuzz.yml and run over a corpus "
              "of %d file(s): %s. This is the check that stops a nightly run "
              "looking healthy while exercising almost "
              "nothing.\n--- output ---\n%s"
              % (step_name, files, "; ".join(wrong), said[-2000:]))

# AND THE WIRING BETWEEN THEM, which running the step cannot see. The
# harness above sets CACHE_HIT itself, so a workflow that hardcodes it
# passes every scenario while the real cache-hit output goes unread --
# found by falsifying exactly that. This is the one assertion here that
# is about text, because wiring is text.
fz = open(os.path.join(ROOT, ".github", "workflows", "fuzz.yml"),
          encoding="utf-8").read()
wiring = [
    ("id: corpus",
     "the cache/restore step must carry `id: corpus` for its cache-hit "
     "output to be referable"),
    ("CACHE_HIT: ${{ steps.corpus.outputs.cache-hit }}",
     "the health step must read CACHE_HIT from that step's output, not from "
     "a literal: a hardcoded value passes every behavioural scenario above "
     "and reports on a cache state nobody looked at"),
]
missing_wiring = [why for text, why in wiring if text not in fz]
check(not missing_wiring,
      "the corpus health step reads the real cache-hit output",
      "fuzz.yml: " + "; ".join(missing_wiring))

# 8. THE GUARD IS RUN, NOT READ. A `make fuzz` with a shell payload in
#    FUZZ_TIME must refuse it, must refuse it BY NAME, and must not run
#    it; a whole number must still get through.
#
#    THE MESSAGE IS PART OF THE ASSERTION, and falsification is what
#    said so. Deleting the $(error) leaves make building build/fuzz_load
#    instead, which needs clang and libFuzzer -- absent on most machines
#    and in most jobs -- so make exits non-zero and creates no sentinel,
#    and "exit != 0 and no sentinel" reads that as a catch. The first
#    version of this check reported PASS with the guard removed. Holding
#    it to the refusal's own words is what tells a refusal apart from a
#    toolchain that was never there.
REFUSAL = "FUZZ_TIME must be a whole number"

with tempfile.TemporaryDirectory() as tmp:
    sentinel = os.path.join(tmp, "payload-ran")
    bad = subprocess.run(
        ["make", "-C", "runtime", "fuzz", "FUZZ_TIME=1; touch %s #" % sentinel],
        cwd=ROOT, capture_output=True, text=True)
    ran = os.path.exists(sentinel)
    said = REFUSAL in (bad.stdout + bad.stderr)
    check(bad.returncode != 0 and not ran and said,
          "make fuzz refuses a FUZZ_TIME carrying a shell command, by name, "
          "and does not run it",
          "`make -C runtime fuzz FUZZ_TIME='1; touch <file>'` exited %d, %s "
          "the file, and %s. runtime/Makefile must refuse a FUZZ_TIME that is "
          "not a whole number, before building anything, and say so -- a make "
          "that merely failed to build the fuzzer looks identical "
          "otherwise.\n--- stdout ---\n%s\n--- stderr ---\n%s"
          % (bad.returncode,
             "CREATED" if ran else "did not create",
             "named FUZZ_TIME" if said else "never mentioned FUZZ_TIME",
             bad.stdout[-2000:], bad.stderr[-2000:]))

# And under -n, where no recipe runs at all, so the only thing that can
# fail is the parse-time guard itself. This is what keeps the check
# above from being satisfiable by a failing build on any machine.
dry_bad = subprocess.run(
    ["make", "-C", "runtime", "-n", "fuzz", "FUZZ_TIME=1; id"],
    cwd=ROOT, capture_output=True, text=True)
check(dry_bad.returncode != 0 and REFUSAL in (dry_bad.stdout + dry_bad.stderr),
      "the refusal is at parse time: `make -n` rejects it with no recipe run",
      "`make -C runtime -n fuzz FUZZ_TIME='1; id'` exited %d. Under -n make "
      "runs nothing, so a guard inside the recipe cannot fire and the value "
      "would reach the shell on the real run. The guard belongs in an "
      "ifneq/$(error) at parse time.\n--- stderr ---\n%s"
      % (dry_bad.returncode, dry_bad.stderr[-2000:]))

# AND EVERY DIGIT GETS THROUGH. `-n` so this needs no clang: a
# parse-time $(error) fires under -n too, and no recipe runs.
#
# `1234567890` is here because the guard is ten $(subst) calls in a
# chain and dropping one of them is a one-character edit. Tested with
# `60` alone -- CI's own value -- a chain that had lost its `9` accepted
# everything it was asked about and rejected `1800`'s neighbours in
# production. The values CI actually passes are checked too, and the
# default is checked by passing nothing.
ACCEPT = ["1234567890",   # every digit, so a missing $(subst) shows up
          "60",           # ci.yml's short pass
          "1800",         # fuzz.yml's nightly default
          None]           # the Makefile's own FUZZ_TIME ?= 60
for value in ACCEPT:
    argv = ["make", "-C", "runtime", "-n", "fuzz"]
    if value is not None:
        argv.append("FUZZ_TIME=" + value)
    good = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    check(good.returncode == 0,
          "make fuzz accepts FUZZ_TIME=%s" % (value if value else "<default>"),
          "`%s` exited %d. The guard on FUZZ_TIME rejects a value it must "
          "accept, so the refusal checks above pass for the wrong "
          "reason.\n--- stderr ---\n%s"
          % (" ".join(argv), good.returncode, good.stderr[-2000:]))

# And the quoting the guard is the last line of defence for. Read
# rather than run, because a digits-only value cannot demonstrate the
# difference -- which is the argument for asserting both.
mk = open(os.path.join(ROOT, "runtime", "Makefile"), encoding="utf-8").read()
check('-max_total_time="$(FUZZ_TIME)"' in mk,
      "runtime/Makefile quotes FUZZ_TIME where it reaches libFuzzer",
      "runtime/Makefile does not contain `-max_total_time=\"$(FUZZ_TIME)\"`. "
      "The parse-time guard restricts the value to digits, and the quotes "
      "are what keeps that guard the only thing between it and /bin/sh. "
      "Keep both.")

for line in oks:
    print("ok - " + line)
if problems:
    print("\nFAIL: %d problem(s)\n" % len(problems), file=sys.stderr)
    for p in problems:
        print("  * " + p + "\n", file=sys.stderr)
    sys.exit(1)
print("\nPASS: %d check(s)" % len(oks))
