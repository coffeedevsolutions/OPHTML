/* The console's default resolver: OPL per-game CFG files.
 *
 * Reads CFG/<ID>.cfg beside a game and maps what OPHTML understands
 * (console_opl_cfg in library.c) onto its settings, so an existing OPL
 * library's per-game compatibility works as it is. main.c registers
 * this with console_set_resolver; a downstream launcher can register
 * its own afterwards to override it.
 *
 * SEPARATE FROM library.c ON PURPOSE. library.c touches no files (its
 * header says so), so the bit that reads a CFG off a drive lives here,
 * over the pure parse and path-derivation it keeps there. Plain POSIX,
 * the same open/read scan.c uses, so tests/test_library.c drives it
 * over a temp directory with the same code the console runs. */

#ifndef CONSOLE_RESOLVER_H
#define CONSOLE_RESOLVER_H

#include "library.h"

/* Resolve `game` from its OPL CFG file. Fills only the fields the CFG
 * carries (the caller zeroes `out` first -- console_resolve does).
 * Returns what console_opl_cfg returns: 1 if the CFG was read and a
 * recognised key was present (the mapped settings may still be empty --
 * e.g. a compat value with only unmapped modes), 0 if there is no ID,
 * no CFG file, or no recognised key. The return is advisory; a 1 does
 * not promise any field was set. */
int console_opl_resolver(const console_game *game, console_settings *out);

#endif /* CONSOLE_RESOLVER_H */
