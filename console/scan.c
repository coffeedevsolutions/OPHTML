/* See scan.h. */

/* opendir, lseek and friends are POSIX, not C99; glibc hides them
 * under -std=c99 without this. The PS2SDK newlib port ignores it. */
#define _POSIX_C_SOURCE 200809L

#include "scan.h"

#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int read_sector(void *user, uint32_t lba, void *buf)
{
    int fd = *(int *)user;
    /* SYSTEM.CNF sits in the first few megabytes of every PS2 disc, so
     * the offset fits a 32-bit off_t even on an 8 GB dual-layer image. */
    if (lseek(fd, (off_t)lba * 2048, SEEK_SET) < 0) return -1;
    return read(fd, buf, 2048) == 2048 ? 0 : -1;
}

static void id_from_image(console_game *g)
{
    int fd = open(g->path, O_RDONLY);
    if (fd < 0) return;
    if (!console_iso_id(read_sector, &fd, g->id, sizeof g->id))
        g->id[0] = '\0';
    close(fd);
}

static int scan_folder(const char *root, const char *folder,
                       console_media media, console_bsd bsd,
                       console_game *games, int n, int max)
{
    char dir[CONSOLE_PATH_MAX];
    DIR *d;
    struct dirent *e;

    if ((size_t)snprintf(dir, sizeof dir, "%s/%s", root, folder) >= sizeof dir)
        return n;
    d = opendir(dir);
    if (d == NULL) return n;

    while (n < max && (e = readdir(d)) != NULL) {
        console_game *g = &games[n];

        if (!console_iso_name(e->d_name, g->title, sizeof g->title,
                              g->id, sizeof g->id))
            continue;
        /* A path that does not fit is skipped, not truncated: a
         * truncated path shows the right title and launches nothing. */
        if ((size_t)snprintf(g->path, sizeof g->path, "%s/%s", dir,
                             e->d_name) >= sizeof g->path)
            continue;
        g->media = (uint8_t)media;
        g->bsd = (uint8_t)bsd;
        if (g->id[0] == '\0') id_from_image(g);
        n++;
    }
    closedir(d);
    return n;
}

int console_scan(const char *root, console_bsd bsd,
                 console_game *games, int n, int max)
{
    n = scan_folder(root, "DVD", CONSOLE_MEDIA_DVD, bsd, games, n, max);
    n = scan_folder(root, "CD", CONSOLE_MEDIA_CD, bsd, games, n, max);
    return n;
}
