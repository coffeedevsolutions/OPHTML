/* The console's writable state on a memory card.
 *
 * console_state (library.h) is parsed and formatted there, with no file
 * touched. This reads and writes it at OPHTML/state on a memory card --
 * mc0: first, then mc1: -- the one writable store that is always present
 * and independent of which game drive is attached, so the launch
 * breadcrumb survives a media swap. The console already POSIX-opens
 * mc0: paths (launch.c finds neutrino.elf there), and mcman/mcserv are
 * among the modules storage.c loads.
 *
 * SEPARATE FROM library.c, like resolver.c, because library.c touches
 * no files. The path-taking `_dir` forms are the reusable primitive and
 * are host-tested over a temp directory; the card-choosing wrappers are
 * mc-specific and bench-tested (Play! has no card slot).
 */

#ifndef CONSOLE_STATE_H
#define CONSOLE_STATE_H

#include "library.h"

/* Read `<base>/OPHTML/state` and parse it into `out`. `out` is zeroed
 * either way. Returns 1 if the file was read and a recognised key
 * found, else 0 (no file, or nothing in it). */
int console_state_load_dir(const char *base, console_state *out);

/* Write `st` to `<base>/OPHTML/state`, creating `<base>/OPHTML` if
 * needed. Returns 1 on success, 0 if the directory or file could not be
 * written. */
int console_state_save_dir(const char *base, const console_state *st);

/* Load from the first memory card that has the file (mc0: then mc1:).
 * `out` is zeroed first; returns 1 if a card's state was read. */
int console_state_load(console_state *out);

/* Save to the first memory card that accepts the write (mc0: then
 * mc1:). Returns 1 on success, 0 if neither card took it -- a launch
 * proceeds either way, so the 0 is silent to the user; a consumer that
 * relies on the breadcrumb having been written must check it. */
int console_state_save(const console_state *st);

#endif /* CONSOLE_STATE_H */
