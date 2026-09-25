/* Walk a device for games, OPL's way: ISOs in DVD/ and CD/ at the root.
 *
 * Plain POSIX -- opendir, open, read -- which the PS2SDK newlib port
 * routes through fileXio once fileXioInit has run, and which the host
 * has natively. So tests/test_library.c scans a directory tree it
 * built in /tmp with the same code the console runs over mass0:. */

#ifndef CONSOLE_SCAN_H
#define CONSOLE_SCAN_H

#include "library.h"

/* Append every ISO under root/DVD and root/CD to games[n..max). `root`
 * is a mount ("mass0:") or, on the host, a directory; it is joined
 * with "/DVD/<name>". A name with no title ID in it gets one from the
 * ISO's SYSTEM.CNF, which costs three sector reads.
 *
 * Returns the new count. A folder that does not exist is not an error:
 * most drives have one of the two, and a drive with neither is simply
 * a drive with no games. */
int console_scan(const char *root, console_bsd bsd,
                 console_game *games, int n, int max);

#endif /* CONSOLE_SCAN_H */
