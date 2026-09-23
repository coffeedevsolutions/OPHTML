/* See library.h. Plain C99: this file is compiled for the EE and, by
 * tests/Makefile, for the host, from the same source. */

#include "library.h"

#include <stdlib.h>
#include <string.h>

console_bsd console_bsd_from_driver(const char *driver)
{
    if (driver == NULL) return CONSOLE_BSD_NONE;
    if (strcmp(driver, "usb") == 0) return CONSOLE_BSD_USB;
    if (strcmp(driver, "ata") == 0) return CONSOLE_BSD_ATA;
    /* mx4sio_bd registers itself as "sdc". "sd" alone is iLink's
     * IEEE1394_bd, which the console does not load, so the exact
     * compare matters: a prefix match would call a FireWire drive an
     * SD card and hand Neutrino the wrong driver. */
    if (strcmp(driver, "sdc") == 0) return CONSOLE_BSD_MX4SIO;
    return CONSOLE_BSD_NONE;
}

const char *console_bsd_arg(console_bsd bsd)
{
    switch (bsd) {
    case CONSOLE_BSD_USB:    return "usb";
    case CONSOLE_BSD_ATA:    return "ata";
    case CONSOLE_BSD_MX4SIO: return "mx4sio";
    case CONSOLE_BSD_MMCE:   return "mmce";
    default:                 return NULL;
    }
}

const char *console_bsd_label(console_bsd bsd)
{
    switch (bsd) {
    case CONSOLE_BSD_USB:    return "USB";
    case CONSOLE_BSD_ATA:    return "HDD";
    case CONSOLE_BSD_MX4SIO: return "SD";
    case CONSOLE_BSD_MMCE:   return "MMCE";
    default:                 return "";
    }
}

static int is_upper(char c) { return c >= 'A' && c <= 'Z'; }
static int is_digit(char c) { return c >= '0' && c <= '9'; }

static char fold(char c)
{
    return (c >= 'A' && c <= 'Z') ? (char)(c - 'A' + 'a') : c;
}

int console_is_title_id(const char *s)
{
    int i;
    if (s == NULL) return 0;
    for (i = 0; i < 4; i++) if (!is_upper(s[i])) return 0;
    if (s[4] != '_') return 0;
    for (i = 5; i < 8; i++) if (!is_digit(s[i])) return 0;
    if (s[8] != '.') return 0;
    return is_digit(s[9]) && is_digit(s[10]);
}

/* Copy n bytes as a string, truncating to cap. Returns 0 on success,
 * -1 if cap is zero (there is nowhere to put even the NUL). */
static int put(char *dst, size_t cap, const char *src, size_t n)
{
    if (cap == 0) return -1;
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n);
    dst[n] = '\0';
    return 0;
}

int console_iso_name(const char *file, char *title, size_t title_cap,
                     char *id, size_t id_cap)
{
    size_t len, stem;
    const char *name = file;

    if (file == NULL || file[0] == '.') return 0;
    len = strlen(file);
    if (len < 5) return 0;
    if (file[len - 4] != '.' || fold(file[len - 3]) != 'i' ||
        fold(file[len - 2]) != 's' || fold(file[len - 1]) != 'o')
        return 0;
    stem = len - 4;

    if (id_cap) id[0] = '\0';
    /* The old OPL format puts the ID and a dot in front. The ID alone
     * with nothing after it ("SLUS_200.02.iso") is a name, not a
     * prefix: keep it as the title AND the ID, since it is both. An ID
     * run straight into more name ("SLUS_200.02X.iso") is neither form,
     * so it is a title and the disc is asked for the ID. */
    if (stem >= 11 && console_is_title_id(file) &&
        (stem == 11 || file[11] == '.')) {
        put(id, id_cap, file, 11);
        if (stem > 12) {
            name = file + 12;
            stem -= 12;
        }
    }
    if (stem == 0) return 0;
    put(title, title_cap, name, stem);
    return 1;
}

int console_cnf_id(const char *cnf, size_t len, char *id, size_t id_cap)
{
    size_t i = 0;

    while (i + 5 <= len) {
        size_t line = i, end = i, s;

        while (end < len && cnf[end] != '\n' && cnf[end] != '\r') end++;
        /* BOOT2 is the PS2 line. A PS1 disc says BOOT, which Neutrino
         * does not boot, so it is deliberately not matched. */
        if (end - line >= 5 && memcmp(cnf + line, "BOOT2", 5) == 0) {
            /* The ID is the file name after the last separator:
             *   BOOT2 = cdrom0:\SLUS_200.02;1
             * Some discs write it with a forward slash or none. */
            s = line + 5;
            for (i = line + 5; i < end; i++)
                if (cnf[i] == '\\' || cnf[i] == '/' || cnf[i] == ':')
                    s = i + 1;
            if (end - s >= 11 && console_is_title_id(cnf + s)) {
                put(id, id_cap, cnf + s, 11);
                return 1;
            }
            return 0;
        }
        i = end + 1;
    }
    return 0;
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Name-compare a directory record's identifier against SYSTEM.CNF,
 * accepting it with or without the ";1" version suffix that ISO9660
 * requires and some mastering tools omit. */
static int is_system_cnf(const unsigned char *name, unsigned n)
{
    static const char want[] = "SYSTEM.CNF";
    unsigned i;
    if (n != 10 && !(n == 12 && name[10] == ';' && name[11] == '1'))
        return 0;
    for (i = 0; i < 10; i++)
        if (fold((char)name[i]) != fold(want[i])) return 0;
    return 1;
}

/* The root of a PS2 disc is small -- SYSTEM.CNF, the ELF, a handful of
 * data files -- so this bounds the walk rather than trusting a length
 * field in a file somebody downloaded. */
#define ROOT_SECTORS_MAX 32

/* And bounds WHICH sectors, not only how many: an extent is a field from
 * the same file. The limit is 2 GiB, in sectors, because that is where
 * the console's reads stop being honest. off_t is 64-bit on the EE, but
 * libcglue hands lseek to fileXio through __fileXioLseekHelper, whose
 * offset is an int (ps2sdk ee/rpc/filexio/src/fileXio_ps2sdk.c), so a
 * seek past 2 GiB is truncated and reads some other sector without an
 * error. SYSTEM.CNF and the root directory sit in a disc's first few
 * megabytes; an extent out here is a damaged or truncated image, and
 * the answer is "no ID", not a read of whatever the truncation lands on.
 * The #179 review found this from a comment that claimed off_t itself
 * was 32-bit; it was wrong about the type and right about the hazard. */
#define ISO_LBA_LIMIT (1u << 20)

int console_iso_id(console_read_fn read, void *user,
                   char *id, size_t id_cap)
{
    unsigned char sec[2048];
    uint32_t root_lba, root_len, n, s;

    /* The primary volume descriptor is at sector 16 in every ISO9660
     * image: type 1, then "CD001". */
    if (read(user, 16, sec) != 0) return 0;
    if (sec[0] != 1 || memcmp(sec + 1, "CD001", 5) != 0) return 0;

    /* The root directory record sits at offset 156: extent at +2, data
     * length at +10, both little-endian halves of a both-endian pair. */
    root_lba = le32(sec + 156 + 2);
    root_len = le32(sec + 156 + 10);
    n = (root_len + 2047) / 2048;
    if (n == 0 || n > ROOT_SECTORS_MAX) n = ROOT_SECTORS_MAX;
    if (root_lba >= ISO_LBA_LIMIT - n) return 0;

    for (s = 0; s < n; s++) {
        unsigned off = 0;
        if (read(user, root_lba + s, sec) != 0) return 0;
        while (off < 2048) {
            unsigned rlen = sec[off], nlen;
            /* A zero length ends the records in this sector; the next
             * one starts at the next sector boundary. */
            if (rlen == 0) break;
            if (rlen < 34 || off + rlen > 2048) return 0;
            nlen = sec[off + 32];
            if (33 + nlen <= rlen && !(sec[off + 25] & 2) &&
                is_system_cnf(sec + off + 33, nlen)) {
                uint32_t lba = le32(sec + off + 2);
                uint32_t len = le32(sec + off + 10);
                if (len > 2048) len = 2048;
                if (lba >= ISO_LBA_LIMIT) return 0;
                if (read(user, lba, sec) != 0) return 0;
                return console_cnf_id((const char *)sec, len, id, id_cap);
            }
            off += rlen;
        }
    }
    return 0;
}

static int title_cmp(const void *a, const void *b)
{
    const console_game *x = a, *y = b;
    const char *p = x->title, *q = y->title;

    while (*p && fold(*p) == fold(*q)) { p++; q++; }
    if (fold(*p) != fold(*q))
        return (unsigned char)fold(*p) < (unsigned char)fold(*q) ? -1 : 1;
    return strcmp(x->path, y->path);
}

void console_sort(console_game *games, size_t n)
{
    if (n > 1) qsort(games, n, sizeof *games, title_cmp);
}

int console_neutrino_args(const console_game *game,
                          char *store, size_t store_cap,
                          char **argv, int argv_cap)
{
    const char *bsd = console_bsd_arg((console_bsd)game->bsd);
    /* -qb is Neutrino's quick boot: it skips the IOP reboot into its
     * own load environment and reads the image through the modules
     * that are ALREADY loaded -- ours. That makes the console's driver
     * set part of the launch, not just the scan: the device the game
     * is on must still be mounted, through fileXio, when Neutrino
     * starts (neutrino ee/loader/src/main.c, the bQuickBoot branches).
     * NHDDL passes it for every BDM and MMCE launch; it is the faster
     * path and the one that frontend runs on hardware. */
    const char *fmt[3] = { "-bsd=", "-dvd=", "-qb" };
    const char *val[3];
    size_t used = 0;
    int i;

    val[0] = bsd;
    val[1] = game->path;
    val[2] = "";
    if (bsd == NULL || game->path[0] == '\0' || argv_cap < 3) return -1;

    for (i = 0; i < 3; i++) {
        size_t a = strlen(fmt[i]), b = strlen(val[i]);
        if (used + a + b + 1 > store_cap) return -1;
        argv[i] = store + used;
        memcpy(store + used, fmt[i], a);
        memcpy(store + used + a, val[i], b);
        store[used + a + b] = '\0';
        used += a + b + 1;
    }
    return 3;
}
