/* See state.h. */

/* open/read/write/mkdir are POSIX, not C99; glibc hides them under
 * -std=c99 without this, and the PS2SDK newlib port ignores it. Same
 * line, same reason, as scan.c and resolver.c. */
#define _POSIX_C_SOURCE 200809L

#include "state.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int console_state_load_dir(const char *base, console_state *out)
{
    char path[CONSOLE_PATH_MAX];
    char buf[256];
    int fd, total = 0, r;

    memset(out, 0, sizeof *out);
    if ((size_t)snprintf(path, sizeof path, "%s/OPHTML/state", base) >= sizeof path)
        return 0;
    fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    while (total < (int)sizeof buf &&
           (r = read(fd, buf + total, (size_t)((int)sizeof buf - total))) > 0)
        total += r;
    close(fd);
    return console_state_parse(buf, (size_t)total, out);
}

int console_state_save_dir(const char *base, const console_state *st)
{
    char dir[CONSOLE_PATH_MAX], path[CONSOLE_PATH_MAX], buf[256];
    int n = console_state_format(st, buf, sizeof buf);
    int fd, w;

    if (n < 0) return 0;
    if ((size_t)snprintf(dir, sizeof dir, "%s/OPHTML", base) >= sizeof dir)
        return 0;
    /* Create the directory; an existing one (EEXIST) is fine, and any
     * other failure surfaces as the open below failing. */
    mkdir(dir, 0777);
    if ((size_t)snprintf(path, sizeof path, "%s/state", dir) >= sizeof path)
        return 0;
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) return 0;
    w = write(fd, buf, (size_t)n);
    close(fd);
    return w == n;
}

/* mc0: first, then mc1:. Reading mc0: paths is the same POSIX open
 * launch.c uses to find neutrino.elf on a card. */
static const char *const cards[] = { "mc0:", "mc1:" };

int console_state_load(console_state *out)
{
    unsigned c;

    memset(out, 0, sizeof *out);
    for (c = 0; c < sizeof cards / sizeof cards[0]; c++)
        if (console_state_load_dir(cards[c], out)) return 1;
    return 0;
}

int console_state_save(const console_state *st)
{
    unsigned c;

    for (c = 0; c < sizeof cards / sizeof cards[0]; c++)
        if (console_state_save_dir(cards[c], st)) return 1;
    return 0;
}
