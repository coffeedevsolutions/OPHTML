#!/usr/bin/env python3
"""Check the documentation site's pages: links, citations, voice, stamps.

WHY THIS EXISTS. docs/site/ carries 46 pages with about 780 `page:`
links, 214 `repo:` links and 183 of those pinned to a line number. The
review of the pull request that added them found eight line pins that
had gone stale while the branch was open (two other pull requests
inserted lines above the cited ones) and one that was wrong when
written, and nothing in the tree could see any of the nine: the only
committed checker compared PNG bytes, and the page verification lived
as a shell snippet in docs/site/ARCHITECTURE.md that nobody ran.

WHAT IT CHECKS, over every page under docs/site/ except _prompts/,
_facts/, ARCHITECTURE.md and the READMEs:

  1. Frontmatter: `id` equals the page's path, `version` equals the
     one site version declared in ARCHITECTURE.md, and the page's
     facts file exists under _facts/.
  2. `page:<id>#<anchor>` links name a written page and a real heading
     on it (headings inside fenced code do not count).
  3. `repo:<path>#L<n>[-L<m>]` links name a file in the tree with the
     line numbers inside it.
  4. Citation drift. docs/site/_citations.tsv records, for every
     line-pinned citation, the text of the cited line when it was
     pinned, plus the lines before and after it. A cited line whose
     text has changed is reported as drifted. `--pin` rewrites the
     record from the tree as it stands; `--fix` relocates a drifted
     citation when the recorded line now occurs exactly once in the
     file, or when several copies exist and exactly one sits between
     the recorded neighbours (a bare `return PS2UI_ERR_RANGE;` repeats,
     its neighbours do not), rewriting the page and the record. The
     ones it cannot place are reported for a hand fix. A citation with
     no record, or a record with no citation, fails until `--pin` is
     run, so the record stays exact.
  4b. THE SAME FOR A FACTS ROW'S `source` CELL, which is where the
     evidence for every claim lives and which nothing checked until
     0.7.0. `packages/layout/src/css.js:598-655` is pinned, drifts and
     relocates exactly as a `repo:` link does, keyed on the first line
     of a range so the range moves as a unit.

     WHY IT WAS WORTH ADDING, measured when it was: 1087 line-anchored
     facts citations in the library and 266 of them had drifted. One
     was broken by the pull request two before this one, which
     inserted a set above GEOMETRY_PROPS -- so the row about the focus
     guard cited a different set with a similar shape, in the file the
     row is about, four commits after a neighbouring row in the same
     file had been re-measured by hand. The page half of this record
     would have caught that in a page; the row carrying the evidence
     was the half with no fence.

     `--pin` AFTER FIXING THE DRIFT, NEVER BEFORE. It writes the
     record from the tree as it stands, so pinning first would have
     rubber-stamped all 266.
  5. Voice: the forbidden words and phrases from ARCHITECTURE.md, em
     dashes and exclamation marks, all outside code, backticks and
     table rows. `Play!` is the emulator's name and is allowed.
  6. Every embedded image exists.
  7. Prose word count: at most 1500 on every page, at least 300 on
     every page outside the project section and the home page.

OUTPUT is TAP-shaped like the other tools/check-*.py: one `ok -` or
`not ok -` line per finding class per page, a summary, exit 1 on any
`not ok`.
"""

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs", "site")
ARCH = os.path.join(SITE, "ARCHITECTURE.md")
PIN = os.path.join(SITE, "_citations.tsv")

FORBIDDEN = [
    "let's", "we", "we'll", "in this section", "in this guide", "simply",
    "seamless", "seamlessly", "robust", "leverage", "powerful",
    "note that", "it's worth noting", "it is worth noting", "keep in mind",
    "as you can see", "of course", "essentially", "basically", "easily",
    "straightforward", "delve", "dive into", "unlock", "empower",
    "journey", "crucial", "vital",
]
FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in FORBIDDEN) + r")\b", re.I)

PAGE_LINK = re.compile(r"\(page:([^)#\s]+)(?:#([^)\s]+))?\)")
REPO_LINK = re.compile(r"\(repo:([^)#\s]+)(?:#L(\d+)(?:-L?(\d+))?)?\)")

# A facts row's `source` cell: `packages/layout/src/css.js:598-655`.
#
# THE UNGUARDED HALF OF THE CITATION STORY. A page's repo: link is
# pinned above and goes red when its line moves. A facts row's source
# cell is where the EVIDENCE for every claim lives, and until 0.7.0 it
# was checked by nothing -- so it drifted silently and the row still
# read `verified`.
#
# Measured when this was added, over the whole library: 1087
# line-anchored citations, 266 of them drifted. One was broken by the
# pull request two before this one, which inserted a set above
# GEOMETRY_PROPS: css.focus.geometry-props then cited a different set
# with a similar shape, in the file the row is about.
# A COMMA LIST IS N CITATIONS, NOT ONE, with or without a space after
# the comma. `runtime/ps2ui.h:653,660,704` used to pin 653 and leave the
# rest unread, because the pattern stopped at the first number: measured
# when this shipped, 122 line numbers across 69 citations in 13 facts
# files, none of them checked. It cost three corrections to one row in a
# single pull request -- `--fix` kept relocating the first number and
# leaving the second behind, each time looking like it had finished.
#
# THIS COMMENT'S FIRST VERSION CARRIED NUMBERS FROM A COMMIT MESSAGE
# WRITTEN THREE PULL REQUESTS EARLIER (59 across 31, six files) and was
# wrong by a third, in the file that exists because a number nobody
# re-read went unchecked. Re-measure these if you touch the pattern.
#
# Group 4 is the tail. Each number in it becomes its own citation with
# its own pin, and relocation rewrites that number alone inside the
# matched text, which is why the token (`:653` or `,660`) is carried
# alongside it rather than the bare integer.
#
# NO PREFIX LIST. This used to require one of
# `packages|runtime|tools|examples|fonts|docs`, which made a citation
# invisible for the accident of where its file sits: `README.md:364`,
# `CHANGELOG.md:44`, `.github/workflows/ci.yml:173`. Measured when the
# list came out: 51 line numbers over 41 citations in 22 facts files,
# 14 of the numbers to README.md and 22 across three workflows (F41a).
# The guard that replaces it is `os.path.isfile` below -- a token is a
# citation when it names a file, and prose naming something else never
# was one.
#
# THOSE TWO UNITS ARE NOT INTERCHANGEABLE and the first version of this
# comment said "50 over 50", restating the member count as a citation
# count. A citation is one `path:N` match; a line number is one member
# of it, and `README.md:120,129,241` is one of the former and three of
# the latter. Review of #160 caught it.
#
# THE SHAPE REQUIREMENT IS WHAT KEEPS PROSE OUT, and it has two arms
# because repo-root files have no slash and `runtime/Makefile` has no
# extension: a path with a slash takes any final segment, a bare
# basename must carry one. Dropping the second arm silently unpinned
# 21 Makefile citations that the prefix list had been checking.
FACTS_CITE = re.compile(
    r"((?:\.?[\w-]+/)+[\w.-]+|[\w-]+\.[A-Za-z0-9]+):(\d+)"
    r"(?:-(\d+))?((?:,\s*\d+(?:-\d+)?)*)")


def cite_members(m):
    r"""[(line, last, token)] for one match, first then the tail.

    `token` is the exact text to rewrite when that member moves, so a
    relocation touches one member and leaves its siblings alone.

    `,\s*` because the tree writes both `:1593,1608` and `:1593, 1608`
    and they are one citation either way. AND A TAIL MEMBER CAN CARRY A
    RANGE: `main.c:2646-2647, 2762-2764` is real, and a pattern that
    stopped at `, 2762` left `-2764` dangling outside the match and
    pinned a single line in the middle of a cited span.
    """
    head_last = int(m.group(3)) if m.group(3) else int(m.group(2))
    out = [(int(m.group(2)), head_last, ":%s" % m.group(2))]
    for tok in re.findall(r",\s*\d+(?:-\d+)?", m.group(4) or ""):
        body = tok.lstrip(", ")
        a, _, b = body.partition("-")
        out.append((int(a), int(b) if b else int(a), tok))
    return out
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")


def pages():
    out = []
    for d, dirs, files in os.walk(SITE):
        dirs[:] = [x for x in dirs if x not in ("_prompts", "_facts")]
        for f in files:
            if not f.endswith(".md") or f in ("ARCHITECTURE.md", "README.md"):
                continue
            path = os.path.join(d, f)
            out.append((os.path.relpath(path, SITE)[:-3], path))
    return sorted(out)


def site_version():
    text = open(ARCH, encoding="utf-8").read()
    m = re.search(r"^Site version: `?([0-9][^`\s]*)`?", text, re.M)
    if not m:
        raise SystemExit("not ok - ARCHITECTURE.md does not declare "
                         "`Site version: <x.y.z>`; every page's version "
                         "stamp is checked against that one line")
    return m.group(1)


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def slug(heading):
    h = heading.replace("`", "").strip().lower()
    h = re.sub(r"[^a-z0-9 _-]", "", h)
    return re.sub(r"\s+", "-", h).strip("-")


def prose_lines(text):
    """Lines that are prose: no fenced code, no table rows, no
    frontmatter, no headings, no image-only lines; backtick spans
    removed from what remains."""
    out = []
    fence = False
    body = text
    if body.startswith("---\n"):
        end = body.find("\n---", 4)
        body = body[end + 4:] if end >= 0 else body
    for line in body.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        s = line.strip()
        if s.startswith("|") or s.startswith("#") or s.startswith("!["):
            continue
        out.append(re.sub(r"`[^`]*`", "", line))
    return out


def headings(text):
    out = set()
    fence = False
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if m:
            out.add(slug(m.group(1)))
    return out


def facts_rows():
    """(facts id, row index, source cell) for every row under _facts/."""
    base = os.path.join(SITE, "_facts")
    for dirpath, _, names in os.walk(base):
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            fid = "_facts/" + os.path.relpath(full, base)[:-3]
            lines = open(full, encoding="utf-8").read().split("\n")
            for i, line in enumerate(lines):
                if not line.startswith("| ") or line.startswith("|---"):
                    continue
                cells = line.split(" | ")
                if len(cells) < 4 or cells[0].lstrip("| ").strip() == "id":
                    continue
                yield fid, full, i, cells


def file_lines(path):
    # DROP THE TRAILING EMPTY ELEMENT. `split("\n")` on a file that ends
    # in a newline yields one more element than the file has lines, and
    # every caller here treats `len(lines)` as the last line number. The
    # cost was two-sided: the range guard admitted a citation to the
    # line after the last one, which pins as empty text and can never
    # drift, and its complaint said "448 lines" of a 447-line ci.yml.
    # Nothing was citing that line once those two were corrected,
    # which is why check 0 in main() asserts the count directly:
    # with no reader left, lengthening this back has no witness.
    with open(os.path.join(ROOT, path), encoding="utf-8",
              errors="replace") as fh:
        lines = fh.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def escape(text):
    return text.replace("\\", "\\\\").replace("\t", "\\t")


def unescape(text):
    return re.sub(r"\\(.)", lambda m: "\t" if m.group(1) == "t" else m.group(1),
                  text)


def read_pin():
    records = {}
    if not os.path.exists(PIN):
        return records
    for raw in open(PIN, encoding="utf-8"):
        raw = raw.rstrip("\n")
        if not raw or raw.startswith("#"):
            continue
        page, path, line, text, before, after = raw.split("\t", 5)
        records[(page, path, int(line))] = (
            unescape(text), unescape(before), unescape(after))
    return records


def write_pin(records):
    with open(PIN, "w", encoding="utf-8") as fh:
        fh.write("# page\trepo path\tline\ttext of that line when pinned"
                 "\tline before\tline after\n"
                 "# Written by tools/check-site-pages.py --pin. Do not "
                 "edit by hand.\n")
        for (page, path, line), (text, before, after) in sorted(records.items()):
            fh.write("%s\t%s\t%d\t%s\t%s\t%s\n"
                     % (page, path, line, escape(text), escape(before),
                        escape(after)))


def window(lines, n):
    """(text, line before, line after) for 1-based line n."""
    return (lines[n - 1],
            lines[n - 2] if n >= 2 else "",
            lines[n] if n < len(lines) else "")


def main(argv):
    mode = "check"
    for a in argv:
        if a in ("--pin", "--fix"):
            mode = a[2:]
        else:
            raise SystemExit("not ok - check-site-pages: unknown argument %r; "
                             "the flags are --pin and --fix" % a)

    version = site_version()
    site = dict(pages())
    texts = {pid: open(p, encoding="utf-8").read() for pid, p in site.items()}
    heads = {pid: headings(t) for pid, t in texts.items()}
    fails = []
    oks = []

    def bad(msg):
        fails.append("not ok - " + msg)

    # 0. file_lines counts lines, not split results.
    #
    # WHY THIS IS A CHECK AND NOT A COMMENT. Every line number in this
    # tool is bounded by `len(lines)`, and `split("\n")` on a file that
    # ends in a newline returns one element more than the file has
    # lines. That let `text.js:183-188` sit green over a 187-line file,
    # pinned on an empty string that can never drift. Shortening
    # `file_lines` by one is caught by the citations that run to the end
    # of their file; LENGTHENING IT BY ONE IS CAUGHT BY NOTHING, because
    # correcting those two citations removed the only readers the
    # phantom line had. So the invariant is asserted here, on bytes this
    # tool writes itself, where both directions fail.
    probe_dir = tempfile.mkdtemp()
    probe = os.path.join(probe_dir, "probe.txt")
    for body, want in (("a\nb\nc\n", 3), ("a\nb\nc", 3), ("", 0),
                       ("\n", 1), ("a\n\n", 2)):
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write(body)
        got = len(file_lines(probe))
        if got != want:
            bad("file_lines(%r) counted %d lines, not %d" % (body, got, want))
    shutil.rmtree(probe_dir)
    oks.append("ok - file_lines counts lines, not split results")

    # 1. frontmatter, facts file
    for pid, text in texts.items():
        fm = frontmatter(text)
        if fm.get("id") != pid:
            bad("%s: frontmatter id is %r, path says %r"
                % (pid, fm.get("id"), pid))
        if fm.get("version") != version:
            bad("%s: version stamp %r, ARCHITECTURE.md says %s"
                % (pid, fm.get("version"), version))
        if not os.path.exists(os.path.join(SITE, "_facts", pid + ".md")):
            bad("%s: no facts file under docs/site/_facts/" % pid)
    oks.append("ok - %d pages carry their own id, version %s, and a facts "
               "file" % (len(site), version))

    # 2. page links
    n_page = 0
    for pid, text in texts.items():
        for m in PAGE_LINK.finditer(text):
            n_page += 1
            target, anchor = m.group(1), m.group(2)
            if target not in site:
                bad("%s: page:%s is not a page" % (pid, target))
            elif anchor and anchor not in heads[target]:
                bad("%s: page:%s#%s names no heading on that page"
                    % (pid, target, anchor))
    oks.append("ok - %d page: links resolve to a page and a heading" % n_page)

    # 3. repo links, and 4. citation drift
    records = read_pin() if mode != "pin" else {}
    seen = set()
    n_repo = n_pinned = 0
    drifted = []
    for pid, text in texts.items():
        for m in REPO_LINK.finditer(text):
            n_repo += 1
            path = m.group(1)
            full = os.path.join(ROOT, path)
            if not os.path.isfile(full):
                bad("%s: repo:%s is not a file in the tree" % (pid, path))
                continue
            if not m.group(2):
                continue
            n_pinned += 1
            lines = file_lines(path)
            first = int(m.group(2))
            last = int(m.group(3)) if m.group(3) else first
            if not (1 <= first <= last <= len(lines)):
                bad("%s: repo:%s#L%d%s is outside the file (%d lines)"
                    % (pid, path, first,
                       "-L%d" % last if last != first else "", len(lines)))
                continue
            key = (pid, path, first)
            seen.add(key)
            current = window(lines, first)
            if mode == "pin":
                records[key] = current
            elif key not in records:
                bad("%s: repo:%s#L%d has no record in _citations.tsv; run "
                    "tools/check-site-pages.py --pin" % (pid, path, first))
            elif records[key][0] != current[0]:
                drifted.append((pid, path, first, last, records[key], current,
                                m.group(0)[1:-1]))
    # 4b. THE SAME TREATMENT FOR A FACTS ROW'S `source` CELL.
    #
    # Same record, same drift test, same relocation; only the place the
    # citation is written differs. Keyed on the first line of a range
    # exactly as a repo: link is, so a range moves as a unit.
    n_facts = 0
    facts_drift = []
    facts_text = {}
    for fid, full, idx, cells in facts_rows():
        facts_text.setdefault(full, open(full, encoding="utf-8").read()
                              .split("\n"))
        for m in FACTS_CITE.finditer(cells[2]):
            path = m.group(1)
            if not os.path.isfile(os.path.join(ROOT, path)):
                continue          # prose naming a path that is not a file
            lines = file_lines(path)
            members = cite_members(m)
            for first, last, token in members:
                if not (1 <= first <= last <= len(lines)):
                    # SAY WHICH OF THE THREE WAYS IT IS WRONG. The
                    # condition folds three of them together and the
                    # message named only the last, so a range written
                    # backwards read as an overrun. F41(a) hit exactly
                    # that: re-pointing `153-154` at a step that had
                    # moved left `156-154`, and the guard caught it and
                    # then called it an overrun of a 447-line file by
                    # line 156, which is true of neither number.
                    why = ("starts before line 1" if first < 1 else
                           "is backwards" if last < first else
                           "is past the end of the file (%d lines)" % len(lines))
                    bad("%s: %s:%d-%d %s" % (fid, path, first, last, why))
                    continue
                n_facts += 1
                key = (fid, path, first)
                seen.add(key)
                current = window(lines, first)
                if mode == "pin":
                    records[key] = current
                elif key not in records:
                    bad("%s: %s:%d has no record in _citations.tsv; run "
                        "tools/check-site-pages.py --pin" % (fid, path, first))
                elif records[key][0] != current[0]:
                    facts_drift.append((fid, full, idx, path, first, last,
                                        records[key], current,
                                        m.group(0), token))

    if mode == "pin":
        records = {k: v for k, v in records.items() if k in seen}
        write_pin(records)
        oks.append("ok - pinned %d line citations into docs/site/_citations.tsv"
                   % len(records))
    else:
        for key in sorted(set(records) - seen):
            bad("%s: _citations.tsv records repo:%s#L%d, which the page no "
                "longer cites; run --pin" % key)
    # Relocation is one pass per page keyed by the exact reference text,
    # never a sequence of text.replace calls: a page that cites L357 and
    # L358 shifts both by one, and replacing "#L357)" then "#L358)" in
    # turn moves the first citation twice.
    moves = {}
    removed, added = set(), {}
    for pid, path, first, last, want, got, ref in drifted:
        if mode != "fix":
            bad("%s: repo:%s#L%d cites a line that changed since it was "
                "pinned\n    pinned: %s\n    now:    %s"
                % (pid, path, first, want[0].strip(), got[0].strip()))
            continue
        lines = file_lines(path)
        where = [i + 1 for i, ln in enumerate(lines) if ln == want[0]]
        if len(where) > 1:
            narrowed = [n for n in where if window(lines, n) == want]
            if len(narrowed) == 1:
                where = narrowed
        if len(where) != 1:
            bad("%s: repo:%s#L%d drifted and its text occurs %d times now; "
                "fix by hand, then --pin\n    pinned: %s\n    now:    %s"
                % (pid, path, first, len(where), want[0].strip(),
                   got[0].strip()))
            continue
        new = where[0]
        new_ref = "repo:%s#L%d" % (path, new)
        if last != first:
            # keep the page's own spelling of the range end
            new_ref += ("-L%d" if "-L" in ref else "-%d") % (last + new - first)
        moves.setdefault(pid, {})[ref] = new_ref
        removed.add((pid, path, first))
        added[(pid, path, new)] = window(lines, new)
        oks.append("ok - %s: moved repo:%s#L%d to #L%d" % (pid, path, first, new))
    if moves:
        for pid, table in moves.items():
            text = open(site[pid], encoding="utf-8").read()
            text = REPO_LINK.sub(
                lambda m: "(" + table.get(m.group(0)[1:-1], m.group(0)[1:-1]) + ")",
                text)
            open(site[pid], "w", encoding="utf-8").write(text)
        for key in removed:
            records.pop(key, None)
        records.update(added)
        write_pin(records)
    # Relocation for the facts rows. One rewrite per row, applied to
    # the whole source cell at once, for the same reason the page pass
    # keys on the exact reference text: a row citing :598 and :656
    # shifts both, and two sequential replaces would move the first
    # twice.
    facts_edits = {}
    for (fid, full, idx, path, first, last, want, got, ref,
         token) in facts_drift:
        if mode != "fix":
            bad("%s: %s:%d cites a line that changed since it was pinned"
                "\n    pinned: %s\n    now:    %s"
                % (fid, path, first, want[0].strip(), got[0].strip()))
            continue
        lines = file_lines(path)
        where = [i + 1 for i, ln in enumerate(lines) if ln == want[0]]
        if len(where) > 1:
            narrowed = [n for n in where
                        if window(lines, n)[1] == want[1]
                        and window(lines, n)[2] == want[2]]
            if len(narrowed) == 1:
                where = narrowed
        if len(where) != 1:
            bad("%s: %s:%d drifted and the pinned line occurs %d time(s); "
                "move it by hand\n    pinned: %s"
                % (fid, path, first, len(where), want[0].strip()))
            continue
        new_first = where[0]
        # ONE MEMBER MOVES, ITS SIBLINGS DO NOT. Rewriting the whole
        # match would drop a comma list's other numbers; rewriting the
        # member's own token inside it keeps them.
        # THE WHOLE SEPARATOR, NOT ITS FIRST CHARACTER. `token[0]` kept
        # the comma and dropped the space, so relocating `:1593, 1608`
        # rewrote it as `:1593,1608` -- right numbers, gratuitous diff,
        # and it falsified this module's own claim to preserve spacing.
        sep = re.match(r"[^0-9]*", token).group(0)
        new_token = "%s%d" % (sep, new_first)
        if last != first:
            new_token += "-%d" % (new_first + last - first)
        # The token already carries its own range, so the rewrite below
        # must not also append one from a sibling.
        facts_edits.setdefault((full, idx), []).append(
            (ref, token, new_token))
        removed.add((fid, path, first))
        added[(fid, path, new_first)] = window(lines, new_first)
        oks.append("ok - %s: moved %s:%d to :%d" % (fid, path, first, new_first))

    for (full, idx), pairs in facts_edits.items():
        lines = facts_text[full]
        cells = lines[idx].split(" | ")
        # Group by the matched text, so a citation whose head AND tail
        # both drifted is rewritten once with both members replaced.
        # Two sequential replaces of the same ref would find the already
        # rewritten copy and move the first member twice.
        by_ref = {}
        for ref, token, new_token in pairs:
            by_ref.setdefault(ref, []).append((token, new_token))
        for ref, edits in by_ref.items():
            # REBUILT IN ONE PASS, NOT ONE re.sub PER MEMBER. A member's
            # NEW value can equal a sibling's OLD token -- 802 moving to
            # 806 in a list that already contains 806 -- and sequential
            # substitution then rewrites the sibling instead, which
            # reorders the list. Same set of lines, and the pins are
            # keyed by line rather than position, so it checked out
            # green; it was still a diff nobody asked for.
            swap = dict(edits)
            m2 = FACTS_CITE.match(ref)
            out = [ref[:m2.start(2) - 1]]          # path, without ':'
            for _first, _last, token in cite_members(m2):
                out.append(swap.get(token, token))
            rebuilt = "".join(out)
            cells[2] = cells[2].replace(ref, rebuilt, 1)
        lines[idx] = " | ".join(cells)
    for full, lines in facts_text.items():
        if any(k[0] == full for k in facts_edits):
            open(full, "w", encoding="utf-8").write("\n".join(lines))
    if mode == "fix" and facts_edits:
        for key in removed:
            records.pop(key, None)
        records.update(added)
        write_pin(records)

    if mode != "pin":
        oks.append("ok - %d repo: links name files in the tree; %d line "
                   "citations checked against _citations.tsv"
                   % (n_repo, n_pinned))
        oks.append("ok - %d facts-row source citations checked against "
                   "_citations.tsv" % n_facts)

    # 5. voice, 6. images, 7. word budget
    for pid, text in texts.items():
        prose = prose_lines(text)
        joined = "\n".join(prose)
        hits = sorted(set(h.lower() for h in FORBIDDEN_RE.findall(joined)))
        if hits:
            bad("%s: forbidden phrase(s) in prose: %s" % (pid, ", ".join(hits)))
        if "—" in joined:
            bad("%s: em dash in prose" % pid)
        bangs = [ln for ln in prose if "!" in ln.replace("Play!", "")]
        if bangs:
            bad("%s: exclamation mark in prose: %s" % (pid, bangs[0].strip()))
        page_dir = os.path.dirname(site[pid])
        for m in IMAGE.finditer(text):
            src = m.group(1)
            if src.startswith("http"):
                continue
            if not (os.path.exists(os.path.join(page_dir, src))
                    or os.path.exists(os.path.join(SITE, src))):
                bad("%s: image %s does not exist" % (pid, src))
        words = len(joined.split())
        if words > 1500:
            bad("%s: %d prose words, budget is 1500" % (pid, words))
        section = pid.split("/")[0]
        if words < 300 and section not in ("project", "index"):
            bad("%s: %d prose words, budget is at least 300" % (pid, words))
    oks.append("ok - voice, images and word budgets hold on every page")

    for line in oks:
        print(line)
    for line in fails:
        print(line)
    print("%s - %d page(s), %d finding(s)"
          % ("not ok" if fails else "ok", len(site), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
