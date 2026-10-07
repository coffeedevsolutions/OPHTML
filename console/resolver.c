/* See resolver.h. */

/* open/read are POSIX, not C99; glibc hides them under -std=c99 without
 * this. The PS2SDK newlib port ignores it. Same line, same reason, as
 * scan.c. */
#define _POSIX_C_SOURCE 200809L

#include "resolver.h"

#include <fcntl.h>
#include <unistd.h>

int console_opl_resolver(const console_game *game, console_settings *out)
{
    char path[CONSOLE_PATH_MAX];
    char buf[4096];
    int fd, total = 0, r;

    if (!console_opl_cfg_path(game, path, sizeof path)) return 0;
    fd = open(path, O_RDONLY);
    if (fd < 0) return 0;

    /* An OPL CFG is a few hundred bytes of "key=value" lines. Cap the
     * read so a mis-named large file cannot be pulled in whole; a CFG
     * past the cap is truncated, which at worst drops later keys and
     * never misreads earlier ones. */
    while (total < (int)sizeof buf &&
           (r = read(fd, buf + total, (size_t)((int)sizeof buf - total))) > 0)
        total += r;
    close(fd);

    return console_opl_cfg(buf, (size_t)total, out);
}
