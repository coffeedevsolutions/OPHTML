#!/usr/bin/env python3
"""Enforce the findings graph in docs/findings.yaml.

A findings ledger that is only prose rots exactly like every other
document in this repository, and this one has the receipts: at the time
this tool was written, `bench-runbook.md` still stated the cache-
writeback bug as fact two headings below the section disproving it, and
`bench-phase1.md` still called the +0.5 UV bias "an unsettled question"
after bench step S10 settled it. Both had been wrong for weeks with
every check green, because nothing connected a claim to its status.

So the relationships are data, and this checks them.

WHAT IT ENFORCES, and why each rule exists rather than being a rule
somebody thought sounded rigorous:

  1. Structure -- ids unique and well formed, no dangling edges, no
     dependency cycles. Table stakes; without it the rest is guessing.

  2. Every finding states a FALSIFIER. This is the most valuable rule
     here and it is not about impact analysis at all. The belief that a
     +0.5 texel bias was wrong survived months, a design doc, a probe
     design and four pull requests -- because nobody had written down
     what would cheaply kill it. A required field forces that question
     at the moment the claim is made, which is the only moment it is
     cheap to answer.

  3. A CONFIRMED finding may not depend on an OVERTURNED one. This is
     the thread between the pins: overturn something in phase 3 and
     every phase 1 finding resting on it fails this rule until a person
     re-confirms it or marks it stale on purpose. Silence is not an
     option the graph offers.

  4. An OVERTURNED finding names what overturned it, so the record
     carries the reason and not just the verdict. Both halves of a dead
     belief are worth keeping; see F-011.

  5. Every evidence.instrument path exists, and VOIDING an instrument
     stales every finding resting on it. This is the step-7 case: the
     tell quad baked at alpha 0x80 and was invisible whether the fault
     was present or not, so fixing it retroactively voided every step-7
     hardware claim that predated the fix -- and nobody enumerated
     which claims those were.

  6. A document citing [F-NNN] where that finding is overturned fails,
     unless it cites [F-NNN:historical] to say it is discussing a dead
     belief deliberately. Exact rather than fuzzy: an earlier design of
     this tool tried to match claim TEXT against document prose, which
     would have been fragile enough to be ignored inside a month.

  7. A locked phase holds no provisional findings. Findings are born
     provisional in the open phase and are promoted when it closes,
     which is the same forcing function as the exit gates in PLAN.md.

Usage:
    tools/check-findings.py                 # check, exit 1 on failure
    tools/check-findings.py --impact F-023  # what breaks if this dies
    tools/check-findings.py --render        # regenerate docs/findings.md
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, "docs", "findings.yaml")
RENDERED = os.path.join(REPO, "docs", "findings.md")

STATUSES = ("provisional", "confirmed", "overturned", "stale")
ID_RE = re.compile(r"^F-\d{3}$")
# A citation in prose. The :historical suffix is how a document says it
# is discussing a dead belief on purpose rather than repeating it.
CITE_RE = re.compile(r"\[(F-\d{3})(:historical)?\]")


def load():
    try:
        import yaml
    except ImportError:
        sys.exit("check-findings: PyYAML not installed")
    with open(LEDGER) as fh:
        doc = yaml.safe_load(fh)
    return doc.get("phases", {}), doc.get("findings", [])


def docs_citing():
    """Every [F-NNN] citation in tracked markdown, by file."""
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "node_modules", "build", "__pycache__")]
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, REPO)
            if rel == "docs/findings.md":     # generated from the ledger
                continue
            try:
                text = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for m in CITE_RE.finditer(text):
                out.append((rel, m.group(1), bool(m.group(2))))
    return out


def check(phases, findings):
    errs = []
    by_id = {}

    for f in findings:
        fid = f.get("id", "<missing id>")
        if not ID_RE.match(str(fid)):
            errs.append(f"{fid}: id must look like F-001")
            continue
        if fid in by_id:
            errs.append(f"{fid}: duplicate id")
        by_id[fid] = f

    for fid, f in by_id.items():
        st = f.get("status")
        if st not in STATUSES:
            errs.append(f"{fid}: status {st!r} not one of {STATUSES}")
        if not str(f.get("claim", "")).strip():
            errs.append(f"{fid}: no claim")

        # Rule 2 -- the one that would have shortened the +0.5 saga.
        if not str(f.get("falsifier", "")).strip():
            errs.append(f"{fid}: no falsifier. A claim with nothing that "
                        f"would kill it is an opinion, not a finding")

        # Rule 1 -- edges resolve.
        for key in ("depends_on", "overturns", "overturned_by"):
            for ref in f.get(key) or []:
                if ref not in by_id:
                    errs.append(f"{fid}: {key} names unknown {ref}")

        # Rule 4 -- a verdict without a reason is half a record.
        if st == "overturned" and not (f.get("overturned_by") or []):
            errs.append(f"{fid}: overturned but does not name what "
                        f"overturned it")

        # Rule 5 -- evidence points at something that exists, and a
        # voided instrument stales what rests on it.
        ev = f.get("evidence") or {}
        inst = ev.get("instrument")
        if inst and not os.path.exists(os.path.join(REPO, inst)):
            errs.append(f"{fid}: evidence.instrument {inst} does not exist")
        if ev.get("instrument_voided") and st == "confirmed":
            errs.append(f"{fid}: confirmed, but its instrument is marked "
                        f"voided -- re-measure or mark stale")

        # Rule 7 -- a locked phase has finished deciding.
        ph = phases.get(f.get("phase"))
        if ph and ph.get("locked") and st == "provisional":
            errs.append(f"{fid}: provisional in locked phase "
                        f"{f.get('phase')}")

    # Rule 3 -- THE THREAD. Overturn something and its dependents cannot
    # stay confirmed in silence.
    for fid, f in by_id.items():
        if f.get("status") != "confirmed":
            continue
        for ref in f.get("depends_on") or []:
            if by_id.get(ref, {}).get("status") == "overturned":
                errs.append(
                    f"{fid}: confirmed, but depends on {ref} which is "
                    f"OVERTURNED. Re-confirm it against the new result "
                    f"or set status: stale")

    # Rule 1b -- cycles.
    seen, stack = set(), set()

    def walk(n):
        if n in stack:
            errs.append(f"dependency cycle through {n}")
            return
        if n in seen:
            return
        seen.add(n)
        stack.add(n)
        for r in by_id.get(n, {}).get("depends_on") or []:
            walk(r)
        stack.discard(n)

    for fid in by_id:
        walk(fid)

    # Rule 6 -- prose may not quietly repeat a dead belief.
    for rel, fid, historical in docs_citing():
        if fid not in by_id:
            errs.append(f"{rel}: cites unknown {fid}")
        elif by_id[fid].get("status") == "overturned" and not historical:
            errs.append(
                f"{rel}: cites {fid}, which is OVERTURNED. Either update "
                f"the passage, or cite [{fid}:historical] if it is "
                f"discussing the dead belief on purpose")
    return errs, by_id


def impact(by_id, target):
    """Everything that would need re-examining if `target` died."""
    hit, frontier = set(), [target]
    while frontier:
        cur = frontier.pop()
        for fid, f in by_id.items():
            if cur in (f.get("depends_on") or []) and fid not in hit:
                hit.add(fid)
                frontier.append(fid)
    return hit


def render(phases, findings):
    by_id = {f["id"]: f for f in findings}
    L = ["<!-- GENERATED by tools/check-findings.py --render. Do not edit:",
         "     edit docs/findings.yaml, which is what CI checks. -->",
         "", "# Findings", "",
         "What this project has established, what killed the things it",
         "stopped believing, and which findings rest on which. Generated",
         "from `docs/findings.yaml`; the relationships in it are enforced",
         "by `tools/check-findings.py` in CI, because a ledger that is only",
         "prose rots like any other document.", ""]

    counts = {}
    for f in findings:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    L += ["| status | count |", "|---|---:|"]
    for st in STATUSES:
        if st in counts:
            L.append(f"| {st} | {counts[st]} |")
    L.append("")

    for pnum in sorted(phases):
        ph = phases[pnum]
        inphase = [f for f in findings if f.get("phase") == pnum]
        if not inphase:
            continue
        lock = "locked" if ph.get("locked") else "**open**"
        L += [f"## Phase {pnum} — {ph.get('title','')} ({lock})", ""]
        for f in sorted(inphase, key=lambda x: x["id"]):
            mark = {"confirmed": "", "provisional": " *(provisional)*",
                    "overturned": " ~~overturned~~", "stale": " ⚠ *(stale)*"}
            L += [f"### {f['id']} — {f['claim']}{mark.get(f['status'],'')}", ""]
            ev = f.get("evidence") or {}
            if ev.get("measurement"):
                L += [f"**Measured:** {ev['measurement']}", ""]
            if ev.get("instrument"):
                v = " — **instrument voided**" if ev.get("instrument_voided") else ""
                L += [f"**Instrument:** `{ev['instrument']}`{v}", ""]
            L += [f"**Falsifier:** {f['falsifier']}", ""]
            for key, label in (("depends_on", "Depends on"),
                               ("overturns", "Overturns"),
                               ("overturned_by", "Overturned by")):
                if f.get(key):
                    refs = ", ".join(f"[{r}](#{r.lower()}) "
                                     f"({by_id[r]['claim'][:48]}…)"
                                     for r in f[key])
                    L += [f"**{label}:** {refs}", ""]
            dependents = impact(by_id, f["id"])
            if dependents:
                L += [f"**Rests on this:** {', '.join(sorted(dependents))}", ""]
            if f.get("note"):
                L += [f["note"].rstrip(), ""]
            if f.get("refs"):
                L += ["*" + ", ".join(f["refs"]) + "*", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impact", metavar="F-NNN")
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    phases, findings = load()
    errs, by_id = check(phases, findings)

    if args.impact:
        if args.impact not in by_id:
            sys.exit(f"no such finding: {args.impact}")
        hit = impact(by_id, args.impact)
        print(f"{args.impact}: {by_id[args.impact]['claim']}")
        if not hit:
            print("  nothing rests on this")
        for fid in sorted(hit):
            f = by_id[fid]
            print(f"  {fid}  [{f['status']:11s}] phase {f['phase']}  "
                  f"{f['claim']}")
        return 0

    if args.render:
        with open(RENDERED, "w") as fh:
            fh.write(render(phases, findings))
        print(f"check-findings: rendered {len(findings)} findings -> "
              f"{os.path.relpath(RENDERED, REPO)}")

    for e in errs:
        print(f"not ok - {e}", file=sys.stderr)
    print(f"{'FAIL' if errs else 'PASS'}: {len(findings)} findings, "
          f"{len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
