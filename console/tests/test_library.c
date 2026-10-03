/* Host-side checks for console/library.c -- the same source the
 * console ELF compiles, built here with the host compiler.
 *
 * usage: test_library
 *
 * Every case is a file name, a SYSTEM.CNF or an ISO somebody could
 * actually have on a drive. The ISO is built in memory, sector by
 * sector, because the question is whether the walk finds the file in
 * a real layout, and a real layout is small enough to write down. */

/* mkdtemp and mkdir are POSIX; see the same line in ../scan.c. */
#define _POSIX_C_SOURCE 200809L

#include "../library.h"
#include "../scan.h"
#include "../resolver.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int checks = 0, failures = 0;

#define CHECK(cond, name) do { \
    checks++; \
    if (cond) { printf("ok %d - %s\n", checks, name); } \
    else { failures++; printf("not ok %d - %s\n", checks, name); } \
} while (0)

/* ------------------------------------------------------------ an ISO */

#define ISO_SECTORS 32
static unsigned char iso[ISO_SECTORS][2048];
static int reads;

static int read_iso(void *user, uint32_t lba, void *buf)
{
    (void)user;
    reads++;
    if (lba >= ISO_SECTORS) return -1;
    memcpy(buf, iso[lba], 2048);
    return 0;
}

static void put32(unsigned char *p, uint32_t v)
{
    /* ISO9660 stores both-endian pairs: little-endian, then big. */
    p[0] = v & 0xff; p[1] = (v >> 8) & 0xff;
    p[2] = (v >> 16) & 0xff; p[3] = v >> 24;
    p[4] = v >> 24; p[5] = (v >> 16) & 0xff;
    p[6] = (v >> 8) & 0xff; p[7] = v & 0xff;
}

/* One directory record; returns its length. */
static unsigned dirent(unsigned char *p, const char *name, unsigned nlen,
                       uint32_t lba, uint32_t len, int dir)
{
    unsigned rlen = 33 + nlen + ((nlen & 1) ? 0 : 1);
    memset(p, 0, rlen);
    p[0] = (unsigned char)rlen;
    put32(p + 2, lba);
    put32(p + 10, len);
    p[25] = dir ? 2 : 0;
    p[32] = (unsigned char)nlen;
    memcpy(p + 33, name, nlen);
    return rlen;
}

static const char CNF[] =
    "BOOT2 = cdrom0:\\SLUS_200.02;1\r\nVER = 1.00\r\nVMODE = NTSC\r\n";

/* A disc laid out the way a PS2 master is: PVD at 16, root directory
 * at 20, SYSTEM.CNF at 22, with the ELF's record in front of it so the
 * walk has to step over a record to find it. `cnf_name` lets a case
 * drop the ";1" suffix. */
static void build_iso(const char *cnf_name)
{
    unsigned off = 0;
    unsigned char *root;

    memset(iso, 0, sizeof iso);
    iso[16][0] = 1;
    memcpy(iso[16] + 1, "CD001", 5);
    dirent(iso[16] + 156, "\0", 1, 20, 2048, 1);

    root = iso[20];
    off += dirent(root + off, "\0", 1, 20, 2048, 1);
    off += dirent(root + off, "\1", 1, 20, 2048, 1);
    off += dirent(root + off, "SLUS_200.02;1", 13, 23, 4096, 0);
    off += dirent(root + off, cnf_name, (unsigned)strlen(cnf_name), 22,
                  (uint32_t)(sizeof CNF - 1), 0);
    memcpy(iso[22], CNF, sizeof CNF - 1);
}

/* ------------------------------------------------------------- tests */

static void test_bsd(void)
{
    CHECK(console_bsd_from_driver("usb") == CONSOLE_BSD_USB, "usb driver is USB");
    CHECK(console_bsd_from_driver("ata") == CONSOLE_BSD_ATA, "ata driver is the HDD");
    CHECK(console_bsd_from_driver("sdc") == CONSOLE_BSD_MX4SIO, "sdc driver is MX4SIO");
    /* "sd" is iLink's block device. A prefix match on "sd" would hand
     * a FireWire drive to Neutrino as -bsd=mx4sio. */
    CHECK(console_bsd_from_driver("sd") == CONSOLE_BSD_NONE, "sd (iLink) is not MX4SIO");
    CHECK(console_bsd_from_driver("usbx") == CONSOLE_BSD_NONE, "no prefix match");
    CHECK(console_bsd_from_driver(NULL) == CONSOLE_BSD_NONE, "NULL driver is none");

    CHECK(strcmp(console_bsd_arg(CONSOLE_BSD_ATA), "ata") == 0, "HDD launches as -bsd=ata");
    CHECK(strcmp(console_bsd_arg(CONSOLE_BSD_MX4SIO), "mx4sio") == 0, "MX4SIO launches as -bsd=mx4sio");
    CHECK(strcmp(console_bsd_arg(CONSOLE_BSD_MMCE), "mmce") == 0, "MMCE launches as -bsd=mmce");
    CHECK(console_bsd_arg(CONSOLE_BSD_NONE) == NULL, "no device, no -bsd=");
    CHECK(strcmp(console_bsd_label(CONSOLE_BSD_MX4SIO), "SD") == 0, "MX4SIO shows as SD");
    CHECK(strlen(console_bsd_label(CONSOLE_BSD_MMCE)) <= 4, "every label fits four characters");
}

static void test_title_id(void)
{
    CHECK(console_is_title_id("SLUS_200.02"), "SLUS_200.02 is an ID");
    CHECK(console_is_title_id("SCES_503.61.Name.iso"), "an ID at the front of a longer string");
    CHECK(!console_is_title_id("slus_200.02"), "lower case is not an ID");
    CHECK(!console_is_title_id("SLUS-200.02"), "a dash is not an ID");
    CHECK(!console_is_title_id("SLUS_20.02"), "short digits are not an ID");
    CHECK(!console_is_title_id(""), "empty is not an ID");
}

static void test_iso_name(void)
{
    char t[CONSOLE_TITLE_MAX], id[CONSOLE_ID_MAX], small[8];

    CHECK(console_iso_name("SLUS_200.02.Ico.iso", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "Ico") == 0 && strcmp(id, "SLUS_200.02") == 0,
          "old OPL name splits into ID and title");
    CHECK(console_iso_name("Shadow of the Colossus.iso", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "Shadow of the Colossus") == 0 && id[0] == '\0',
          "a plain name is the title, with no ID");
    CHECK(console_iso_name("Okami.ISO", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "Okami") == 0, "the extension is matched in any case");
    CHECK(console_iso_name("SLUS_200.02.iso", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "SLUS_200.02") == 0 && strcmp(id, "SLUS_200.02") == 0,
          "an ID with no title is both");
    CHECK(console_iso_name("SLUS_200.02X.iso", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "SLUS_200.02X") == 0 && id[0] == '\0',
          "an ID run into more name is a title, not an OPL prefix");
    CHECK(console_iso_name("SLUS_200.02..iso", t, sizeof t, id, sizeof id) == 1 &&
          strcmp(t, "SLUS_200.02.") == 0 && strcmp(id, "SLUS_200.02") == 0,
          "an ID, a dot and no title keeps the whole stem as the title");
    CHECK(console_iso_name("._Okami.iso", t, sizeof t, id, sizeof id) == 0,
          "macOS resource forks are not games");
    CHECK(console_iso_name(".iso", t, sizeof t, id, sizeof id) == 0, "no name, no game");
    CHECK(console_iso_name("Okami.bin", t, sizeof t, id, sizeof id) == 0, "only .iso is listed");
    CHECK(console_iso_name("Okami.iso.part", t, sizeof t, id, sizeof id) == 0,
          "a partial download is not an ISO");
    CHECK(console_iso_name("A long title here.iso", small, sizeof small, id, sizeof id) == 1 &&
          strcmp(small, "A long ") == 0, "a title truncates to its buffer rather than overrunning");
}

static void test_cnf(void)
{
    char id[CONSOLE_ID_MAX];
    static const char slash[] = "BOOT2 = cdrom0:/SCES_503.61;1\n";
    static const char bare[] = "VER = 1.00\nBOOT2 =cdrom0:\\SLPM_650.51;1";
    static const char ps1[] = "BOOT = cdrom:\\SCUS_944.26;1\r\n";
    static const char junk[] = "BOOT2 = cdrom0:\\GAME.ELF;1\r\n";

    CHECK(console_cnf_id(CNF, sizeof CNF - 1, id, sizeof id) == 1 &&
          strcmp(id, "SLUS_200.02") == 0, "the BOOT2 line gives the ID");
    CHECK(console_cnf_id(slash, sizeof slash - 1, id, sizeof id) == 1 &&
          strcmp(id, "SCES_503.61") == 0, "a forward slash separates too");
    CHECK(console_cnf_id(bare, sizeof bare - 1, id, sizeof id) == 1 &&
          strcmp(id, "SLPM_650.51") == 0, "BOOT2 on the last line, without a newline");
    CHECK(console_cnf_id(ps1, sizeof ps1 - 1, id, sizeof id) == 0,
          "a PS1 disc's BOOT line is not matched");
    CHECK(console_cnf_id(junk, sizeof junk - 1, id, sizeof id) == 0,
          "a boot file that is not an ID gives no ID");
}

static void test_iso_id(void)
{
    char id[CONSOLE_ID_MAX];

    build_iso("SYSTEM.CNF;1");
    reads = 0;
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 1 &&
          strcmp(id, "SLUS_200.02") == 0, "SYSTEM.CNF found in the root and read");
    CHECK(reads == 3, "three sector reads: PVD, root, SYSTEM.CNF");

    build_iso("SYSTEM.CNF");
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 1,
          "a SYSTEM.CNF without its ;1 suffix is still found");

    build_iso("system.cnf;1");
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 1,
          "the name compare ignores case");

    build_iso("README.TXT;1");
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0,
          "no SYSTEM.CNF, no ID");

    build_iso("SYSTEM.CNF;1");
    iso[16][1] = 'X';
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0,
          "not an ISO9660 image, no ID");

    build_iso("SYSTEM.CNF;1");
    iso[20][0] = 20; /* a record shorter than its own fixed fields */
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0,
          "a corrupt directory record stops the walk");

    /* A root extent past 2 GiB is refused before it is read: on the EE
     * the seek would be truncated to an int by fileXio and land on some
     * other sector without an error. The read counter is the check,
     * because the host's 64-bit lseek would fail the read honestly and
     * hide the difference. */
    build_iso("SYSTEM.CNF;1");
    put32(iso[16] + 156 + 2, 0x200000);
    reads = 0;
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0 && reads == 1,
          "a root extent past 2 GiB is refused without being read");

    build_iso("SYSTEM.CNF;1");
    put32(iso[16] + 156 + 2, 0xffffffffu);
    reads = 0;
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0 && reads == 1,
          "a root extent at the top of the 32-bit range is refused, not wrapped");

    build_iso("SYSTEM.CNF;1");
    put32(iso[20] + 34 + 34 + 46 + 2, 0x100000); /* after ".", ".." and the ELF */
    reads = 0;
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0 && reads == 2,
          "a SYSTEM.CNF extent past 2 GiB is refused without being read");

    build_iso("SYSTEM.CNF;1");
    put32(iso[16] + 156 + 2, 4000); /* root past the end of the image */
    CHECK(console_iso_id(read_iso, NULL, id, sizeof id) == 0,
          "a failed read stops the walk");
}

static void test_sort(void)
{
    console_game g[4];
    memset(g, 0, sizeof g);
    strcpy(g[0].title, "okami");      strcpy(g[0].path, "mass0:/DVD/b.iso");
    strcpy(g[1].title, "Ico");        strcpy(g[1].path, "mass0:/DVD/a.iso");
    strcpy(g[2].title, "Okami");      strcpy(g[2].path, "mass0:/DVD/a.iso");
    strcpy(g[3].title, "Ape Escape"); strcpy(g[3].path, "mass1:/CD/c.iso");
    console_sort(g, 4);
    CHECK(strcmp(g[0].title, "Ape Escape") == 0 && strcmp(g[1].title, "Ico") == 0,
          "sorted by title");
    CHECK(strcmp(g[2].path, "mass0:/DVD/a.iso") == 0 &&
          strcmp(g[3].path, "mass0:/DVD/b.iso") == 0,
          "titles equal but for case fall back to the path");
}

static void test_neutrino(void)
{
    console_game g;
    console_settings s;
    char store[512], tiny[16];
    char *argv[8];
    int argc;

    memset(&g, 0, sizeof g);
    strcpy(g.path, "mass0:/DVD/Shadow of the Colossus.iso");
    g.bsd = CONSOLE_BSD_ATA;

    /* NULL settings is the plain three-argument launch, unchanged. */
    argc = console_neutrino_args(&g, NULL, store, sizeof store, argv, 8);
    CHECK(argc == 3, "three arguments");
    CHECK(argc == 3 && strcmp(argv[0], "-bsd=ata") == 0, "-bsd= names the device");
    CHECK(argc == 3 && strcmp(argv[1], "-dvd=mass0:/DVD/Shadow of the Colossus.iso") == 0,
          "-dvd= carries the full path, spaces and all, as one argument");
    CHECK(argc == 3 && strcmp(argv[2], "-qb") == 0, "quick boot");

    /* All-empty settings is identical to NULL: no option is emitted. */
    memset(&s, 0, sizeof s);
    CHECK(console_neutrino_args(&g, &s, store, sizeof store, argv, 8) == 3,
          "empty settings emit the same three arguments as NULL");

    /* A field that is set adds its option, between -dvd and -qb, with
     * the option's "-flag=" prefix and the field's value. */
    strcpy(s.gc, "23");
    argc = console_neutrino_args(&g, &s, store, sizeof store, argv, 8);
    CHECK(argc == 4 && strcmp(argv[2], "-gc=23") == 0,
          "-gc= carries the compat digits and sits before -qb");
    CHECK(argc == 4 && strcmp(argv[3], "-qb") == 0, "-qb stays last");

    /* Every option, in struct order: gc, gsm, mc0, mc1. */
    strcpy(s.gsm, "fp2:1");
    strcpy(s.vmc0, "mass0:/VMC/a.bin");
    strcpy(s.vmc1, "mass0:/VMC/b.bin");
    argc = console_neutrino_args(&g, &s, store, sizeof store, argv, 8);
    CHECK(argc == 7, "bsd, dvd, gc, gsm, mc0, mc1, qb");
    CHECK(argc == 7 && strcmp(argv[2], "-gc=23") == 0 &&
          strcmp(argv[3], "-gsm=fp2:1") == 0 &&
          strcmp(argv[4], "-mc0=mass0:/VMC/a.bin") == 0 &&
          strcmp(argv[5], "-mc1=mass0:/VMC/b.bin") == 0 &&
          strcmp(argv[6], "-qb") == 0,
          "options appear in struct order with their prefixes");

    /* gsm without gc: the gap is closed, not left as an empty slot. */
    memset(&s, 0, sizeof s);
    strcpy(s.gsm, "fp1");
    argc = console_neutrino_args(&g, &s, store, sizeof store, argv, 8);
    CHECK(argc == 4 && strcmp(argv[2], "-gsm=fp1") == 0,
          "an unset earlier field leaves no hole");

    g.bsd = CONSOLE_BSD_NONE;
    CHECK(console_neutrino_args(&g, NULL, store, sizeof store, argv, 8) == -1,
          "an unknown device is refused, not launched as something else");

    g.bsd = CONSOLE_BSD_USB;
    CHECK(console_neutrino_args(&g, NULL, tiny, sizeof tiny, argv, 8) == -1,
          "a command line that does not fit is refused, not truncated");
    CHECK(console_neutrino_args(&g, NULL, store, sizeof store, argv, 2) == -1,
          "too few argv slots is refused");

    /* argv overflow counts the option arguments too: seven needed, six
     * offered, refused rather than written past the array. */
    memset(&s, 0, sizeof s);
    strcpy(s.gc, "3"); strcpy(s.gsm, "fp2");
    strcpy(s.vmc0, "mass0:/VMC/a.bin"); strcpy(s.vmc1, "mass0:/VMC/b.bin");
    CHECK(console_neutrino_args(&g, &s, store, sizeof store, argv, 6) == -1,
          "an option that would overflow argv is refused, not truncated");
}

/* A resolver a launcher could register: it sets gc for one id and
 * leaves every other game alone, so the test sees both a hit and a
 * miss through the same seam. */
static int stub_resolver(const console_game *game, console_settings *out)
{
    if (strcmp(game->id, "SLUS_200.02") == 0) {
        strcpy(out->gc, "3");
        return 1;
    }
    return 0;
}

static void test_resolver(void)
{
    console_game g;
    console_settings s;

    memset(&g, 0, sizeof g);

    /* No resolver: resolve yields all-empty settings, a plain launch.
     * The 0xff poison proves resolve zeroes the struct rather than
     * trusting the caller to. */
    console_set_resolver(NULL);
    memset(&s, 0xff, sizeof s);
    console_resolve(&g, &s);
    CHECK(s.gc[0] == '\0' && s.gsm[0] == '\0' && s.vmc0[0] == '\0' &&
          s.vmc1[0] == '\0', "no resolver: settings come back all-empty");

    /* A registered resolver fills what it knows for a game it knows. */
    console_set_resolver(stub_resolver);
    strcpy(g.id, "SLUS_200.02");
    memset(&s, 0xff, sizeof s);
    console_resolve(&g, &s);
    CHECK(strcmp(s.gc, "3") == 0, "a known game gets the resolver's settings");
    CHECK(s.gsm[0] == '\0', "fields the resolver did not set stay empty");

    /* A game the resolver does not know comes back empty, not poisoned
     * and not carrying the previous game's settings. */
    strcpy(g.id, "SLES_500.00");
    memset(&s, 0xff, sizeof s);
    console_resolve(&g, &s);
    CHECK(s.gc[0] == '\0',
          "an unknown game gets empty settings, not stale ones");

    console_set_resolver(NULL);   /* leave the global clean for later tests */
}

static void test_opl_cfg(void)
{
    console_settings s;
    console_game g;
    char path[CONSOLE_PATH_MAX];

    /* Mode 2 | Mode 3 == 0x06 == 6: both map, ascending. */
    memset(&s, 0, sizeof s);
    CHECK(console_opl_cfg("$Compatibility=6\n", 17, &s) == 1 &&
          strcmp(s.gc, "23") == 0, "$Compatibility 6 -> gc 23");

    /* Mode 2 | Mode 5 == 0x12 == 18: digits stay in ascending order. */
    memset(&s, 0, sizeof s);
    console_opl_cfg("$Compatibility=18\n", 18, &s);
    CHECK(strcmp(s.gc, "25") == 0, "$Compatibility 18 -> gc 25, in order");

    /* Mode 7 alone (0x40 == 64): recognised, but mapped to nothing --
     * OPL Mode 7 is not Neutrino 7. */
    memset(&s, 0, sizeof s);
    CHECK(console_opl_cfg("$Compatibility=64\n", 18, &s) == 1 &&
          s.gc[0] == '\0', "OPL Mode 7 is dropped, not mapped to -gc 7");

    /* Mode 1 alone (0x01): no -gc counterpart, dropped. */
    memset(&s, 0, sizeof s);
    console_opl_cfg("$Compatibility=1\n", 17, &s);
    CHECK(s.gc[0] == '\0', "OPL Mode 1 has no -gc counterpart");

    /* All eight bits set (255): only 2, 3, 5 survive. */
    memset(&s, 0, sizeof s);
    console_opl_cfg("$Compatibility=255\n", 19, &s);
    CHECK(strcmp(s.gc, "235") == 0, "every bit set maps to exactly 235");

    /* Value 0 is a present key with no modes: recognised, empty gc. */
    memset(&s, 0, sizeof s);
    CHECK(console_opl_cfg("$Compatibility=0\n", 17, &s) == 1 &&
          s.gc[0] == '\0', "$Compatibility 0 is found but maps to nothing");

    /* Other keys are ignored; the compat line is still found among them,
     * and CRLF line endings parse. */
    memset(&s, 0, sizeof s);
    CHECK(console_opl_cfg("$DMA=1\r\n$Compatibility=4\r\n", 26, &s) == 1 &&
          strcmp(s.gc, "3") == 0, "other keys ignored, CRLF fine");

    /* No compat key at all: nothing found, nothing set. */
    memset(&s, 0, sizeof s);
    CHECK(console_opl_cfg("$DMA=1\n", 7, &s) == 0 && s.gc[0] == '\0',
          "a CFG with no $Compatibility resolves nothing");

    /* Path derivation from a DVD game with an ID. */
    memset(&g, 0, sizeof g);
    strcpy(g.path, "mass0:/DVD/Shadow of the Colossus.iso");
    strcpy(g.id, "SLUS_200.02");
    CHECK(console_opl_cfg_path(&g, path, sizeof path) == 1 &&
          strcmp(path, "mass0:/CFG/SLUS_200.02.cfg") == 0,
          "CFG path is root + /CFG/<ID>.cfg");

    /* A CD game roots off "/CD/" the same way. */
    strcpy(g.path, "mass1:/CD/Ape Escape.iso");
    CHECK(console_opl_cfg_path(&g, path, sizeof path) == 1 &&
          strcmp(path, "mass1:/CFG/SLUS_200.02.cfg") == 0,
          "a CD game roots off /CD/");

    /* No ID: no CFG to find. */
    g.id[0] = '\0';
    CHECK(console_opl_cfg_path(&g, path, sizeof path) == 0,
          "a game with no ID has no CFG path");

    /* A path with no media folder cannot be rooted. */
    strcpy(g.id, "SLUS_200.02");
    strcpy(g.path, "mass0:/loose/Game.iso");
    CHECK(console_opl_cfg_path(&g, path, sizeof path) == 0,
          "a path with no /DVD/ or /CD/ has no CFG path");
}

/* Defined with the scan helpers further down; used here too. */
static void touch(const char *path, const void *data, size_t len);

/* The OPL resolver end to end, reading a real CFG off a temp tree the
 * same way scan.c reads a drive -- so the file read, the path
 * derivation and the compat mapping are exercised together, through
 * console_resolve, exactly as main.c calls it. */
static void test_opl_resolver(void)
{
    console_game g;
    console_settings s;
    char root[] = "/tmp/console-cfg-XXXXXX", p[512];

    if (mkdtemp(root) == NULL) { perror("mkdtemp"); exit(2); }
    snprintf(p, sizeof p, "%s/CFG", root); mkdir(p, 0755);
    snprintf(p, sizeof p, "%s/CFG/SLUS_200.02.cfg", root);
    touch(p, "$Compatibility=6\n", 17);

    memset(&g, 0, sizeof g);
    snprintf(g.path, sizeof g.path, "%s/DVD/Ico.iso", root);
    strcpy(g.id, "SLUS_200.02");

    console_set_resolver(console_opl_resolver);
    console_resolve(&g, &s);
    CHECK(strcmp(s.gc, "23") == 0,
          "the OPL resolver reads CFG/<ID>.cfg and maps its compat");

    /* A game with no CFG file resolves to empty, not an error, and
     * console_resolve's zeroing means no stale settings leak in. */
    strcpy(g.id, "SLES_999.99");
    console_resolve(&g, &s);
    CHECK(s.gc[0] == '\0', "a game with no CFG file resolves to empty");

    console_set_resolver(NULL);
}

/* The MOCK=1 build's list, as main.c builds it. The previewer takes
 * these lines in file order and the console sorts them, so the file has
 * to already be in console_sort's order or the emulator frame and the
 * previewer frame disagree for a reason neither of them shows. */
static void test_mock_sorted(void)
{
    static const struct { const char *title, *id; int media, bsd; } mock[] = {
#define MOCK(t, i, m, b) { t, i, m, b },
#include "../mock_library.h"
#undef MOCK
    };
    enum { N = sizeof mock / sizeof mock[0] };
    static console_game g[N];
    int k, same = 1, ids = 1;

    for (k = 0; k < N; k++) {
        snprintf(g[k].path, sizeof g[k].path, "mock:/DVD/%s.iso", mock[k].title);
        snprintf(g[k].title, sizeof g[k].title, "%s", mock[k].title);
        if (!console_is_title_id(mock[k].id)) ids = 0;
    }
    console_sort(g, N);
    for (k = 0; k < N; k++)
        if (strcmp(g[k].title, mock[k].title) != 0) same = 0;
    CHECK(same, "mock_library.h is already in console_sort's order");
    CHECK(ids, "every mock ID is a well-formed title ID");
    CHECK(N > 10, "the mock list is longer than the built-in theme's ten rows");
}

/* ------------------------------------------------------ a real tree */

static void touch(const char *path, const void *data, size_t len)
{
    FILE *f = fopen(path, "wb");
    if (f == NULL) { perror(path); exit(2); }
    if (len) fwrite(data, 1, len, f);
    fclose(f);
}

static const console_game *find(const console_game *g, int n, const char *title)
{
    int i;
    for (i = 0; i < n; i++) if (strcmp(g[i].title, title) == 0) return &g[i];
    return NULL;
}

/* The scan over a directory laid out the way people lay out a drive:
 * both of OPL's folders, both naming styles, a macOS resource fork and
 * a file that is not a game. */
static void test_scan(void)
{
    static console_game games[16];
    char root[] = "/tmp/console-scan-XXXXXX", p[512], deep[400];
    const console_game *g;
    int n;

    if (mkdtemp(root) == NULL) { perror("mkdtemp"); exit(2); }
    snprintf(p, sizeof p, "%s/DVD", root); mkdir(p, 0755);
    snprintf(p, sizeof p, "%s/CD", root);  mkdir(p, 0755);

    build_iso("SYSTEM.CNF;1");
    snprintf(p, sizeof p, "%s/DVD/Ico.iso", root);
    touch(p, iso, 24 * 2048);
    snprintf(p, sizeof p, "%s/DVD/SCES_503.61.Okami.iso", root);
    touch(p, "not read", 8);
    snprintf(p, sizeof p, "%s/DVD/._Ico.iso", root);
    touch(p, "fork", 4);
    snprintf(p, sizeof p, "%s/DVD/notes.txt", root);
    touch(p, "", 0);
    snprintf(p, sizeof p, "%s/CD/Ape Escape.iso", root);
    touch(p, "too short to be an image", 24);

    n = console_scan(root, CONSOLE_BSD_USB, games, 0, 16);
    CHECK(n == 3, "three games: two DVDs and a CD, nothing else");

    g = find(games, n, "Ico");
    CHECK(g && strcmp(g->id, "SLUS_200.02") == 0,
          "a plain name gets its ID from the image's SYSTEM.CNF");
    snprintf(p, sizeof p, "%s/DVD/Ico.iso", root);
    CHECK(g && strcmp(g->path, p) == 0, "the path is the root joined with DVD/");
    CHECK(g && g->media == CONSOLE_MEDIA_DVD && g->bsd == CONSOLE_BSD_USB,
          "media from the folder, device from the caller");

    g = find(games, n, "Okami");
    CHECK(g && strcmp(g->id, "SCES_503.61") == 0,
          "an ID in the name is used without opening the image");

    g = find(games, n, "Ape Escape");
    CHECK(g && g->id[0] == '\0' && g->media == CONSOLE_MEDIA_CD,
          "an unreadable image is still listed, with no ID");

    CHECK(console_scan(root, CONSOLE_BSD_USB, games, 0, 2) == 2,
          "the scan stops at the caller's capacity");
    CHECK(console_scan(root, CONSOLE_BSD_USB, games, 5, 16) == 8,
          "the scan appends after the games already found");

    /* A root long enough that the folder fits and a file in it does
     * not. "/./" changes the length and not the directory. */
    snprintf(deep, sizeof deep, "%s", root);
    while (strlen(deep) + 3 + 4 + 1 + 5 <= CONSOLE_PATH_MAX - 1)
        strcat(deep, "/.");
    snprintf(p, sizeof p, "%s/DVD/a.iso", root);
    touch(p, "", 0);
    n = console_scan(deep, CONSOLE_BSD_USB, games, 0, 16);
    CHECK(find(games, n, "a") != NULL, "a short name under a long root fits");
    CHECK(find(games, n, "Okami") == NULL,
          "a path past CONSOLE_PATH_MAX is skipped, not truncated");

    snprintf(p, sizeof p, "%s/nothing-here", root);
    CHECK(console_scan(p, CONSOLE_BSD_USB, games, 0, 16) == 0,
          "a drive with no DVD/ or CD/ has no games, and no error");

    snprintf(p, sizeof p, "rm -rf '%s'", root);
    if (system(p) != 0) fprintf(stderr, "could not remove %s\n", root);
}

int main(void)
{
    test_bsd();
    test_title_id();
    test_iso_name();
    test_cnf();
    test_iso_id();
    test_sort();
    test_neutrino();
    test_resolver();
    test_opl_cfg();
    test_opl_resolver();
    test_scan();
    test_mock_sorted();
    printf("1..%d\n", checks);
    if (failures) {
        fprintf(stderr, "%d of %d checks failed\n", failures, checks);
        return 1;
    }
    return 0;
}
