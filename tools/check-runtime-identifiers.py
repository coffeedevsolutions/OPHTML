#!/usr/bin/env python3
"""Does every identifier the runtime's comments name actually exist?

WHY THIS EXISTS. `runtime/ps2ui.h` and `runtime/ps2ui.c` are the two
files `ps2ui vendor-runtime` hands to somebody who never cloned. Their
comments are the API documentation for that reader: there is no other
document in the wheel. So a comment naming a function or macro that
does not exist is not a typo, it is a wrong manual shipped inside the
artifact.

Three were found at once, all shipped in 0.6.0, AND THEY ARE TWO
DIFFERENT DEFECTS. The distinction is worth the lines because the
lessons differ and this checker catches both.

INVENTIONS -- wrong at the moment of writing. Nothing was ever called
this, so the day the comment is written it is already false:

    ps2ui.h    ps2ui_focus_rect      0 declarations, ever. Written into
                                     the ps2ui_offset_set comment while
                                     documenting F27: the paragraph
                                     explaining the newest call named an
                                     imaginary one for the geometry
                                     query. The real answer is
                                     ctx->focus_nodes[ctx->focus].
    ps2ui.c    PS2UI_MAX_LIST_ROWS   0 #defines, ever, including at the
                                     commit that wrote its comment.

A COMMENT THAT OUTLIVED A DELIBERATE REMOVAL -- true when written, and
nobody's error:

    ps2ui.c    PS2UI_MAX_TEXTURES    the macro WAS defined when the
                                     comment was written. 1d2542e added
                                     the comment; cd8def8 (#52, "Delete
                                     the table ceilings") removed the
                                     macro 4h26m later the same day, and
                                     did not sweep the comments citing
                                     it -- in a file another change was
                                     touching that afternoon. The
                                     comment was then false for 20 days.

That second one is F28's class exactly -- "not drift: a correct removal
whose documentation was never followed through" -- and a fourth
recorded instance of it, beside F28's own eight sites, #121's stale
counts and #125's B8. It is also the most interesting of the three,
because no one got it wrong: the removal was right and the sweep was
the missing half.

A fence that catches both "you named something that never was" and
"someone deleted what you named" is worth more than one that catches
only carelessness. This catches both, because it asks the same lexical
question of each.

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

THREE SHAPES PASS, AND NONE IS REACHABLE TODAY. Recorded so the next
reader does not re-derive them, and checked rather than assumed:

  - A token with `/` on either side is treated as a path, so
    `ps2ui_bogus/` would pass. Contrived, and the alternative --
    enumerating paths -- is worse.
  - split_comments treats everything outside a comment as code, so a
    token appearing only in a string literal would count as existing.
    Checked: no ps2ui_* or PS2UI_* token appears in any string literal
    in either C file today.
  - The staleness rule below is one-sided. It fires when a
    NAMED_AS_ABSENT entry stops being cited, not when its identifier
    becomes real -- if ps2ui_overlay_push is ever written, the entry
    persists unremarked. Harmless, since the comment would then be
    wrong for a reason this checker does not test, but it is half of
    what "stopped being needed" means.

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
# (path, mode). "c" reads the comments and treats everything else as
# the code that defines things; "prose" reads the whole file, because
# there is no code in it.
#
# README.md IS IN THE CORPUS BECAUSE THE SAME INVENTION WAS THERE.
# ps2ui_focus_rect was written into README.md:366 by the same commit
# that put it in ps2ui.h, and this PR corrected the README by hand
# while the checker watched only the pair. Running this file's own
# logic over the pre-fix README flags it with no new rules -- so the
# fence stopped one line short of the defect it was built for.
#
# Scoped to README.md rather than all of docs/. Measured: docs/PLAN.md
# names seven non-runtime tokens (the removed MAX_* family,
# PS2UI_REQUIRE_FONTS, PS2UI_SAMPLE_OPLENV) and tutorial-uc3.md names
# PS2UI_LAYOUT -- environment variables and build flags, each wanting
# an entry, for no demonstrated defect. The README is the file with one.
FILES = (("runtime/ps2ui.h", "c"),
         ("runtime/ps2ui.c", "c"),
         # THE STARTER, which the wheel now carries beside the runtime
         # pair. `--starter` writes it into a stranger's project, so
         # its comments are API documentation for the same reader the
         # header serves -- and it is comment-dense by design, since
         # its whole job is explaining what a newcomer may change. It
         # is also the file most likely to acquire a stale name later,
         # for the same reason.
         #
         # Green the day it was added: 9 distinct identifiers, every
         # one of them defined. Added for the reason #129 gave for
         # pulling README.md in, with the difference stated rather than
         # glossed -- the README had a demonstrated defect and this
         # does not. The check was already written; the file is newly
         # shipped; waiting for the first stale name is how the
         # header's own three got there.
         #
         # The starter Makefile is deliberately NOT here. `EE_BIN =
         # ps2ui_app.elf` matches the ps2ui_* pattern and defines
         # nothing, so it would need a rule before it needed
         # including, and one token does not earn one.
         ("packages/baker/ps2ui_bake/starter/main.c", "c"),
         ("README.md", "prose"))

# Only the C pair defines things. A token existing solely in the README
# does not make it real.
DEFINING = ("runtime/ps2ui.h", "runtime/ps2ui.c")

# A FILE THAT OWNS A PREFIX MAY DEFINE ITS OWN NAMES, and only its own.
#
# The starter has three build-time macros of its own -- PS2UI_STARTER_
# ARENA, _SCREEN, _NOPAD -- which its comments explain because a reader
# is invited to change them. They are #defined in that file and nowhere
# in the runtime, which is correct: they are not API. So the starter's
# comments resolve against the C pair PLUS its own code.
#
# SCOPED TO A PREFIX RATHER THAN JUST ADDING THE FILE TO DEFINING, and
# the difference is the whole point. Adding it to DEFINING would let a
# token that exists only in the starter satisfy a comment in ps2ui.h --
# which is precisely the hole #129 closed when it kept README.md out of
# DEFINING so a README-only name could not make an identifier look
# real. The starter owns PS2UI_STARTER_*; it does not get to vouch for
# anything else, and nothing else gets to vouch for it.
#
# Found by adding the file: the first version of this corpus entry went
# red on PS2UI_STARTER_ARENA, and a review that measured the same file
# by hand had reported it green at 9 identifiers. Running it is what
# found the tenth.
SELF_DEFINING = {
    "packages/baker/ps2ui_bake/starter/main.c": "PS2UI_STARTER_",
}

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
    ("README.md", "ps2ui_overlay_push"):
        "README.md:424, the same point for the same reason",
    ("README.md", "ps2ui_bake"):
        "README.md:113, `python3 -m ps2ui_bake` -- the Python module, "
        "which exists; not slash-adjacent, so the path rule cannot see it",
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
    real, own, mentioned = set(), set(), {}
    for rel, mode in FILES:
        src = open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()
        if mode == "c":
            prose, code = split_comments(src)
        else:
            prose, code = src, ""
        if rel in DEFINING:
            real |= set(TOKEN.findall(code))
        elif rel in SELF_DEFINING:
            pre = SELF_DEFINING[rel]
            own |= set(t for t in TOKEN.findall(code) if t.startswith(pre))
        for m in TOKEN.finditer(prose):
            if _is_path_component(prose, m):
                continue
            mentioned.setdefault(m.group(0), set()).add(rel)

    print("ok - read %d identifier(s) out of the comments in %s"
          % (len(mentioned), " and ".join(f for f, _ in FILES)))

    for tok in sorted(mentioned):
        if tok in real:
            continue
        # A prefix-owned name, resolved against the one file allowed to
        # define it -- and only when that file is the one naming it.
        if tok in own and all(
                f in SELF_DEFINING and tok.startswith(SELF_DEFINING[f])
                for f in mentioned[tok]):
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
        msg = ("%s is named in %s and exists nowhere in the "
               "runtime. ps2ui.h and ps2ui.c are the only API "
               "documentation inside the wheel, and README.md is the "
               "front page, so this is a wrong manual shipped to "
               "somebody who cannot read the repository. Either the "
               "identifier is wrong, or the prose is about something that "
               "was removed or was deliberately never written -- in which "
               "case add it to NAMED_AS_ABSENT in "
               "%s with a reason." % (tok, where, os.path.basename(__file__)))
        print("not ok - " + msg)
        fail.append(tok)

    # The splitter's own precondition, checked rather than assumed.
    for rel, mode in FILES:
        if mode != "c":
            continue
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
