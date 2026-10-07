#!/usr/bin/env python3
"""No new commit carries a personal email address.

WHY THIS EXISTS, AND WHAT IT CANNOT DO. An exposure audit of this public
repository found a work email on 3 commits and
`<account>@<hostname>.lan` on 26 more. Both were accidents of a machine's
default `user.email`, and both are permanent: commit metadata is
published the instant it is pushed, and is indexed and forked from there.

So be exact about what this is. It is a DETECTOR, not a preventer. By
the time it runs, the address is already on GitHub. Its value is that
the next one is found while it is still one commit on one branch, which
is the only point at which a rewrite is cheap -- rather than being found
by an audit, 29 commits later, when rewriting means changing all 394
SHAs and dangling every SHA citation in these docs.

The preventive halves live elsewhere and are named here so nobody
mistakes this for them:

  * `tools/git-hooks/pre-commit`, which refuses the commit before the
    object exists. It reads the SAME list this does, and --selftest below
    asserts the two agree, because two copies of an allowlist is the
    drift this project keeps finding.
  * GitHub's "Block command line pushes that expose my email", which is
    an account setting, cannot live in a repository, and would have
    prevented both findings on its own.

THE HISTORICAL 29 ARE NOT A FAILURE HERE, deliberately. This checks a
RANGE -- what a branch or a push adds -- so it is green on a clean branch
and stays green without anyone having to declare an exception list of
SHAs that would rot. `--history` prints the whole-history tally instead,
and never fails: that number is a matter of record, and the decision
about it was made and written down (see tools/git-hooks/allowed-emails).

    tools/check-commit-identities.py                  # origin/main..HEAD
    tools/check-commit-identities.py --base <sha>      # <sha>..HEAD
    tools/check-commit-identities.py --history         # the tally, never fails
    tools/check-commit-identities.py --selftest        # hook and checker agree
"""
import fnmatch
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "tools", "git-hooks", "allowed-emails")
HOOK = os.path.join(ROOT, "tools", "git-hooks", "pre-commit")
NULL_SHA = "0" * 40


def globs():
    out = []
    with open(LIST, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.append(ln)
    if not out:
        print("%s declares no patterns, so every address would be refused "
              "and nothing could be committed." % LIST, file=sys.stderr)
        sys.exit(1)
    return out


def allowed(email, patterns):
    return any(fnmatch.fnmatchcase(email, g) for g in patterns)


def git(*args):
    r = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                       text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def have(rev):
    return rev and rev != NULL_SHA and git("rev-parse", "--verify",
                                           "--quiet", rev + "^{commit}")[0] == 0


def resolve_base(asked):
    """The range's start, and the sentence saying which one was used."""
    if have(asked):
        return asked, "the base given on the command line"
    for fallback in ("origin/main", "main"):
        if have(fallback):
            return fallback, ("%s, because no usable base was given" % fallback)
    return None, ("nothing: this checkout has neither the base given nor "
                  "origin/main, so there is no range to check")


def commits(base):
    rng = "%s..HEAD" % base if base else "HEAD"
    code, out, err = git("log", "--format=%H%x1f%ae%x1f%ce%x1f%s", rng)
    if code != 0:
        print("cannot read `git log %s`:\n%s" % (rng, err), file=sys.stderr)
        sys.exit(1)
    rows = []
    for ln in out.split("\n"):
        if ln:
            h, ae, ce, subject = ln.split("\x1f", 3)
            rows.append((h, ae, ce, subject))
    return rng, rows


def selftest(patterns):
    """The hook and this file answer the same for the same address.

    Two implementations of one allowlist is exactly the shape this
    project keeps catching, so they are run against each other rather
    than read side by side. The cases include one that is allowed only
    by a glob, so a hook that had quietly stopped expanding `*` would
    fail here rather than in a year.
    """
    OK = "139636658+coffeedevsolutions@users.noreply.github.com"
    BAD = "blake@macbookpro.lan"
    # (author, committer, accepted?) -- THE LAST TWO ARE THE POINT.
    # Testing one address in both slots cannot tell a hook that checks
    # both from one that checks only the committer, and falsification
    # found exactly that: dropping AUTHOR from the loop passed. The
    # asymmetric pair is also the real-world case, since a merge made on
    # github.com sets the committer to noreply@github.com and leaves the
    # author as whoever pushed.
    cases = [
        (OK, OK, True),
        ("noreply@anthropic.com", "noreply@github.com", True),
        ("49699333+dependabot[bot]@users.noreply.github.com",
         "noreply@github.com", True),
        ("someone@example.com", "someone@example.com", False),
        (BAD, BAD, False),
        ("user@users.noreply.github.com.evil.test", OK, False),
        (BAD, "noreply@github.com", False),      # author only
        (OK, BAD, False),                        # committer only
        ("", "", False),
    ]
    bad = []
    for author, committer, want in cases:
        mine = allowed(author, patterns) and allowed(committer, patterns)
        env = dict(os.environ)
        env.update({
            "GIT_AUTHOR_EMAIL": author or "x@y.invalid",
            "GIT_AUTHOR_NAME": "T",
            "GIT_COMMITTER_EMAIL": committer or "x@y.invalid",
            "GIT_COMMITTER_NAME": "T",
        })
        if not author:
            # An empty address cannot be handed to git var, so only this
            # file's answer is checked for it.
            theirs = False
        else:
            theirs = subprocess.run(["sh", HOOK], cwd=ROOT, env=env,
                                    capture_output=True).returncode == 0
        if mine != want or theirs != want:
            bad.append("author %r committer %r: wanted %s, this file said %s, "
                       "the hook said %s"
                       % (author, committer, want, mine, theirs))
    if bad:
        print("FAIL: the hook and this checker disagree, or disagree with the "
              "expected answer:", file=sys.stderr)
        for b in bad:
            print("  * " + b, file=sys.stderr)
        sys.exit(1)
    print("ok - the hook and this checker agree on %d author/committer "
          "pair(s), including one allowed only through a glob, one that "
          "merely ends in an allowed domain, and one bad address in each "
          "slot on its own" % len(cases))


def history(patterns):
    code, out, _ = git("log", "--all", "--format=%ae%x1f%ce")
    tally = {}
    for ln in out.split("\n"):
        if not ln:
            continue
        for email in ln.split("\x1f"):
            tally[email] = tally.get(email, 0) + 1
    print("Every identity in this repository's history, as a matter of record:")
    for email, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %-55s %5d  %s"
              % (email, n, "ok" if allowed(email, patterns) else "NOT ALLOWED"))
    print("\nThis mode never fails. Rewriting history was considered and "
          "declined; tools/git-hooks/allowed-emails says why.")


def main():
    argv = sys.argv[1:]
    patterns = globs()
    if "--selftest" in argv:
        selftest(patterns)
        return
    if "--history" in argv:
        history(patterns)
        return
    asked = ""
    if "--base" in argv:
        asked = argv[argv.index("--base") + 1]
    base, why = resolve_base(asked)
    rng, rows = commits(base)
    print("ok - range is `%s`, from %s" % (rng, why))
    bad = [(h, ae, ce, s) for h, ae, ce, s in rows
           if not allowed(ae, patterns) or not allowed(ce, patterns)]
    if bad:
        print("\nFAIL: %d commit(s) in %s carry an address this repository "
              "does not accept.\n" % (len(bad), rng), file=sys.stderr)
        for h, ae, ce, s in bad:
            print("  * %s  author <%s>  committer <%s>\n    %s"
                  % (h[:12], ae, ce, s[:70]), file=sys.stderr)
        print("\n  This is a PUBLIC repository, so these are already "
              "published. Fix them NOW, while it is still this branch:\n"
              "    git config user.email <id>+<user>@users.noreply.github.com\n"
              "    git rebase --root --exec 'git commit --amend --no-edit "
              "--reset-author'   # or amend just these\n"
              "  Then install the hook so it cannot recur:\n"
              "    git config core.hooksPath tools/git-hooks\n",
              file=sys.stderr)
        sys.exit(1)
    print("ok - %d commit(s) in the range, every author and committer address "
          "accepted" % len(rows))
    print("\nPASS")


main()
