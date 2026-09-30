/* The console's game library: everything about finding and describing
 * a game that does not need a PS2 to run.
 *
 * WHY THIS IS ITS OWN FILE. The console ELF has three halves: bringing
 * up storage (storage.c), handing a game to a loader (launch.c), and
 * deciding what the files it finds MEAN -- which name is a title, which
 * is a title ID, which bytes in an ISO say what disc it is, what
 * command line Neutrino needs. Only the first two need an IOP. This
 * half is plain C99 over caller-supplied bytes, so tests/test_library.c
 * runs it on the host against the same code the console compiles, and
 * the parts most likely to be wrong on somebody's odd filename are the
 * parts a test can reach.
 *
 * NOTHING HERE ALLOCATES OR TOUCHES A FILE. The ISO reader takes a
 * callback that returns one sector; the console's callback reads a
 * file, the test's reads an array. */

#ifndef CONSOLE_LIBRARY_H
#define CONSOLE_LIBRARY_H

#include <stddef.h>
#include <stdint.h>

/* "mass0:/DVD/" plus an exFAT name of up to 255 bytes does not fit in
 * 256, and a path that silently truncates launches nothing while
 * showing a title that looks fine. The scan refuses a path that does
 * not fit rather than storing a prefix of it. */
#define CONSOLE_PATH_MAX  320
/* Titles are what the UI shows. A theme's slot has its own capacity
 * and ps2ui_slot_set truncates to it on a character boundary, so this
 * only has to be at least as long as any sensible slot. */
#define CONSOLE_TITLE_MAX 128
/* "SLUS_200.02" and its NUL. */
#define CONSOLE_ID_MAX    12

/* Where a game lives, in the vocabulary Neutrino's -bsd= takes. The
 * console only knows the devices it loads drivers for; see storage.c. */
typedef enum {
    CONSOLE_BSD_NONE = 0,
    CONSOLE_BSD_USB,
    CONSOLE_BSD_ATA,      /* the internal HDD, exFAT on MBR or GPT */
    CONSOLE_BSD_MX4SIO,   /* microSD on an SIO2 adapter */
    CONSOLE_BSD_MMCE      /* microSD in an SD2PSX / MemCard PRO2 slot */
} console_bsd;

/* OPL's two folders. Neutrino does not need it -- it reads the disc
 * type from the image -- but the UI shows it and OPL's layout sorts by
 * it, so it is kept. */
typedef enum {
    CONSOLE_MEDIA_DVD = 0,
    CONSOLE_MEDIA_CD
} console_media;

typedef struct {
    char    path[CONSOLE_PATH_MAX];   /* "mass0:/DVD/Name.iso" */
    char    title[CONSOLE_TITLE_MAX]; /* "Name" */
    char    id[CONSOLE_ID_MAX];       /* "SLUS_200.02", or "" if unknown */
    uint8_t media;                    /* console_media */
    uint8_t bsd;                      /* console_bsd */
} console_game;

/* BDM reports which driver backs a massN: mount through an ioctl. The
 * names are the drivers' own: "usb", "ata", and "sdc" for MX4SIO. An
 * unknown name is CONSOLE_BSD_NONE, and the scan skips that device
 * rather than guessing a -bsd= Neutrino would then fail on. */
console_bsd console_bsd_from_driver(const char *driver);

/* The -bsd= value Neutrino takes, or NULL for CONSOLE_BSD_NONE. */
const char *console_bsd_arg(console_bsd bsd);

/* What the UI calls the device: "USB", "HDD", "SD" or "MMCE". Four
 * characters at most, so a slot sized for "USB" plus one fits them. */
const char *console_bsd_label(console_bsd bsd);

/* 1 if s[0..10] is an OPL-style title ID ("SLUS_200.02": four capital
 * letters, underscore, three digits, dot, two digits). */
int console_is_title_id(const char *s);

/* Read an ISO's file name the way OPL names them.
 *
 *   "SLUS_200.02.Name.iso"  -> id "SLUS_200.02", title "Name"
 *   "Name.iso"              -> id "",            title "Name"
 *
 * Returns 1 for an ISO, 0 for anything the console should not list:
 * another extension, an empty name, or a dot-file. The dot-file rule is
 * not tidiness: macOS writes "._Name.iso" beside every file it copies
 * to an exFAT or FAT drive, and those are 4 KiB of resource fork that
 * would otherwise appear as a second copy of every game. */
int console_iso_name(const char *file, char *title, size_t title_cap,
                     char *id, size_t id_cap);

/* Pull the title ID out of a SYSTEM.CNF's text: the file name on the
 * BOOT2 line, "BOOT2 = cdrom0:\SLUS_200.02;1". Returns 1 and writes
 * `id` only when what it finds is a well-formed title ID. */
int console_cnf_id(const char *cnf, size_t len, char *id, size_t id_cap);

/* One 2048-byte ISO sector at `lba` into `buf`; 0 on success. */
typedef int (*console_read_fn)(void *user, uint32_t lba, void *buf);

/* Find SYSTEM.CNF in an ISO9660 image's root directory and read the
 * title ID from it. This is the fallback for a file named "Name.iso",
 * which is how most people name them; OPL's ART and CFG folders are
 * keyed by the ID, so a game without one has no cover and no settings.
 * Returns 1 on success. Reads at most a few dozen sectors, and none
 * past 2 GiB into the image (library.c says why). */
int console_iso_id(console_read_fn read, void *user,
                   char *id, size_t id_cap);

/* Alphabetical by title, ignoring ASCII case, then by path so two
 * copies of one game on two drives keep a stable order. */
void console_sort(console_game *games, size_t n);

/* Per-game settings a resolver decides and the launch applies, one
 * field per Neutrino option, each holding the option's VALUE (not its
 * "-flag=" prefix) or "" to leave the option off. The strings are what
 * Neutrino's command line takes verbatim, so a resolver's only job is
 * to fill them; console_neutrino_args does the quoting.
 *
 *   gc    game compatibility, a run of mode digits Neutrino concatenates
 *         (0 fast reads, 2 sync reads, 3 unhook syscalls, 5 DVD-DL,
 *         7 fix buffer overrun; 1 is a dummy). "-gc=23" is two of them.
 *         OPL stores these as a BITMASK, so the OPL->Neutrino resolver
 *         translates bits to this digit string -- that mapping is the
 *         resolver's work, not this file's.
 *   gsm   video mode as "v:c": v forces the mode (fp1 240p/288p,
 *         fp2 480p/576p, 1080ix1..3), c is field-flip compat (1,2,3).
 *         "fp2" alone is legal; "fp2:1" sets both.
 *   vmc0  virtual memory card image for slot 0, a path on a mounted
 *   vmc1  drive, or "" for the real card. This is card-IMAGE emulation
 *         (Neutrino's -mc0=/-mc1=), a different thing from gc's compat.
 *
 * Patches (Neutrino cheats) are deliberately absent: they are not in
 * the core option set this struct mirrors, and belong to a later slice.
 *
 * A caller that wants today's plain launch passes NULL for settings,
 * which is exactly "every field empty". */
typedef struct {
    char gc[8];                /* "23", or "" */
    char gsm[16];              /* "fp2:1", or "" */
    char vmc0[CONSOLE_PATH_MAX];
    char vmc1[CONSOLE_PATH_MAX];
} console_settings;

/* Build the command line that hands `game` to Neutrino:
 *
 *   -bsd=<device> -dvd=<path> [-gc=..] [-gsm=..] [-mc0=..] [-mc1=..] -qb
 *
 * The bracketed options appear only for a `settings` field that is set;
 * `settings` may be NULL, which is the same as all-empty and reproduces
 * the plain three-argument launch. The strings are written into `store`
 * and `argv` points into it. argv[0] is NOT included: the loader
 * supplies it from the ELF's own path. Returns argc, or -1 if the
 * game's device has no -bsd=, or the store or argv would overflow. */
int console_neutrino_args(const console_game *game,
                          const console_settings *settings,
                          char *store, size_t store_cap,
                          char **argv, int argv_cap);

/* A resolver decides a game's settings, keyed by whatever it likes --
 * usually `game->id`. It writes into `out` (already zeroed when called,
 * so it only sets the fields it knows) and returns 1 if it found
 * anything, 0 if the game is unknown to it. The return is advisory:
 * console_resolve produces a valid settings either way.
 *
 * This is the seam the product plugs into. OPHTML's console links no
 * resolver of its own yet -- the default is "none", which is a plain
 * launch -- so a downstream launcher registers one that reads its
 * database and this file never learns what a database is. */
typedef int (*console_resolver)(const console_game *game,
                                console_settings *out);

/* Register the resolver console_resolve will call, or NULL to clear it.
 * One resolver at a time; the last registered wins. */
void console_set_resolver(console_resolver fn);

/* Fill `out` with `game`'s settings: zero it, then let the registered
 * resolver (if any) set what it knows. With no resolver, `out` is left
 * all-empty, which console_neutrino_args treats exactly as NULL. A
 * launcher calls this, then hands `out` to console_launch. */
void console_resolve(const console_game *game, console_settings *out);

#endif /* CONSOLE_LIBRARY_H */
