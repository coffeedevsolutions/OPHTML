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

# 5. THE GUARD IS RUN, NOT READ. A `make fuzz` with a shell payload in
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
