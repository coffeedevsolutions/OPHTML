#!/usr/bin/env python3
"""Does every identifier the runtime's comments name actually exist?

WHY THIS EXISTS. `runtime/ps2ui.h` and `runtime/ps2ui.c` are the two
files `ps2ui vendor-runtime` hands to somebody who never cloned. Their
comments are the API documentation for that reader: there is no other
document in the wheel. So a comment naming a function or macro that
does not exist is not a typo, it is a wrong manual shipped inside the
artifact.

Three were found at once, and each had shipped in 0.6.0:

    ps2ui.h    ps2ui_focus_rect      never existed. Written into the
                                     ps2ui_offset_set comment while
                                     documenting F27 -- the paragraph
                                     explaining the newest call named
                                     an imaginary one for the geometry
                                     query, and the real answer is
                                     ctx->focus_nodes[ctx->focus].
    ps2ui.c    PS2UI_MAX_TEXTURES    cited as the bound on a linear
                                     scan. It is a uint16_t field.
    ps2ui.c    PS2UI_MAX_LIST_ROWS   cited as the bound on a digit
                                     loop that bounds itself.

THE SOURCE CONTRADICTED ITSELF AND NOBODY NOTICED. ps2ui.h:288 already
said, correctly, that PS2UI_MAX_TEXTURES "used to sit here ... They are
gone" -- while ps2ui.c cited it twice as a live bound. The header was
right for months and the .c file was wrong for months, in the same
shipped pair.

WHAT THIS CHECKS, AND WHY IT IS NOT PROSE MATCHING. Every ps2ui_* and
PS2UI_* token appearing in a comment must also appear OUTSIDE a comment
somewhere in the pair -- i.e. be declared, defined, or used. That is a
lexical question, not a claim about meaning, which is the distinction
check-findings.py rule 6's note draws when it warns off matching claim
text against prose.

THE ONE EXCEPTION IS DELIBERATE AND EXPLICIT. Prose that says a thing
was REMOVED has to name it to be worth reading, and ps2ui.h:288 is
exactly that: a paragraph explaining why three validation ceilings are
gone. Rather than guess from wording -- "used to", "are gone" -- which
would be the prose matching this avoids, those identifiers are listed
below with a reason. Adding to the list is a deliberate act a reviewer
can see in a diff.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ("runtime/ps2ui.h", "runtime/ps2ui.c")

# Identifiers a comment may name even though the runtime does not
# define them, because the comment's subject IS their absence. Each
# needs a reason, and the list is checked for staleness below.
# SCOPED TO ONE FILE EACH, and that is not tidiness. A global list let
# the original defect straight back in: PS2UI_MAX_TEXTURES is
# legitimately named as absent in ps2ui.h:288, and with an unscoped
# entry that also licensed ps2ui.c citing it as a live bound -- which
# is precisely the comment this checker was written to catch.
# Falsification found it on the second sabotage.
NAMED_AS_ABSENT = {
    ("runtime/ps2ui.h", "PS2UI_MAX_TEXTURES"):
        "ps2ui.h:288, the paragraph explaining that the validation "
        "ceilings were removed at v6",
    ("runtime/ps2ui.h", "PS2UI_MAX_SLOTS"):   "same paragraph",
    ("runtime/ps2ui.h", "PS2UI_MAX_SCREENS"): "same paragraph",
    ("runtime/ps2ui.c", "PS2UI_MAX_SLOTS"):
        "ps2ui.c:180, the note on why ps2ui_load has no count ceiling -- "
        "past tense, and found only once these entries were scoped per "
        "file, because the ps2ui.h entry had been covering it silently",
    ("runtime/ps2ui.h", "ps2ui_overlay_push"):
        "ps2ui.h:628, 'There is deliberately no ps2ui_overlay_push' -- an "
        "API named in order to say it was not written, and why",
}

# Trailing `_` excluded on purpose: a comment writing PS2UI_TEXKIND_* or
# PS2UI_MAX_* means the family, not an identifier, and chopping at the
# underscore invents a token nobody wrote. Both forms appear here and
# both were false positives on this file's first run.
TOKEN = re.compile(r"\b(?:ps2ui_[a-z0-9_]*[a-z0-9]|PS2UI_[A-Z0-9_]*[A-Z0-9])\b")

# ...and a token inside a path is a file, not an API. `ps2ui.h:453`
# cites packages/baker/ps2ui_bake/gs.py, which exists and is not a
# runtime symbol. Checked by looking at the characters around the match
# rather than by listing the paths, so a new one needs no edit here.
def _is_path_component(src, m):
    before = src[m.start() - 1] if m.start() else " "
    after = src[m.end()] if m.end() < len(src) else " "
    # A `/` on either side, and nothing else. An earlier version also
    # treated a following `.` as a path, which silently swallowed
    # "There is deliberately no ps2ui_overlay_push." -- a sentence
    # ending in a full stop. The NAMED_AS_ABSENT staleness check below
    # caught that on the next run, which is the reason it is there.
    return before == "/" or after == "/"


def split_comments(src):
    """Return (comment_text, code_text). Crude but sufficient for C99
    with no string literals containing comment markers, which this pair
    has none of -- asserted below rather than assumed."""
    out_c, out_k, i, n = [], [], 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out_c.append(src[i:j]); i = j
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out_c.append(src[i:j]); i = j
        else:
            out_k.append(src[i]); i += 1
    return "".join(out_c), "".join(out_k)


def main():
    fail = []
    real, mentioned = set(), {}
    for rel in FILES:
        src = open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()
        comments, code = split_comments(src)
        real |= set(TOKEN.findall(code))
        for m in TOKEN.finditer(comments):
            if _is_path_component(comments, m):
                continue
            mentioned.setdefault(m.group(0), set()).add(rel)

    print("ok - read %d identifier(s) out of the comments in %s"
          % (len(mentioned), " and ".join(FILES)))

    for tok in sorted(mentioned):
        if tok in real:
            continue
        # Per FILE, so an identifier excused in the header is not
        # thereby excused in the source.
        unexcused = sorted(f for f in mentioned[tok]
                           if (f, tok) not in NAMED_AS_ABSENT)
        if not unexcused:
            print("ok - %s is named only as absent (%s)"
                  % (tok, NAMED_AS_ABSENT[(sorted(mentioned[tok])[0], tok)]))
            continue
        where = ", ".join(unexcused)
        msg = ("%s is named in a comment in %s and exists nowhere in the "
               "runtime. These two files are the only API documentation "
               "inside the wheel, so this is a wrong manual shipped to "
               "somebody who cannot read the repository. Either the "
               "identifier is wrong, or the prose is about something that "
               "was removed or was deliberately never written -- in which "
               "case add it to NAMED_AS_ABSENT in "
               "%s with a reason." % (tok, where, os.path.basename(__file__)))
        print("not ok - " + msg)
        fail.append(tok)

    # The splitter's own precondition, checked rather than assumed.
    for rel in FILES:
        src = open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()
        if re.search(r'"[^"\n]*(/\*|\*/)[^"\n]*"', src):
            print("not ok - %s has a string literal containing a comment "
                  "marker, which this file's splitter does not handle" % rel)
            fail.append(rel)
    if not fail:
        print("ok - no string literal carries a comment marker, so the "
              "comment/code split above is sound")

    stale = sorted("%s in %s" % (t, f) for (f, t) in NAMED_AS_ABSENT
               if f not in mentioned.get(t, ()))
    if stale:
        print("not ok - NAMED_AS_ABSENT lists %s, which no comment mentions "
              "any more. Drop the entry." % ", ".join(stale))
        fail += stale
    else:
        print("ok - every NAMED_AS_ABSENT entry is still cited by a comment")

    print("%s - %d identifier(s) checked, %d problem(s)"
          % ("not ok" if fail else "ok", len(mentioned), len(fail)))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
