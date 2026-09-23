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
    char store[512], tiny[16];
    char *argv[8];
    int argc;

    memset(&g, 0, sizeof g);
    strcpy(g.path, "mass0:/DVD/Shadow of the Colossus.iso");
    g.bsd = CONSOLE_BSD_ATA;
    argc = console_neutrino_args(&g, store, sizeof store, argv, 8);
    CHECK(argc == 3, "three arguments");
    CHECK(argc == 3 && strcmp(argv[0], "-bsd=ata") == 0, "-bsd= names the device");
    CHECK(argc == 3 && strcmp(argv[1], "-dvd=mass0:/DVD/Shadow of the Colossus.iso") == 0,
          "-dvd= carries the full path, spaces and all, as one argument");
    CHECK(argc == 3 && strcmp(argv[2], "-qb") == 0, "quick boot");

    g.bsd = CONSOLE_BSD_NONE;
    CHECK(console_neutrino_args(&g, store, sizeof store, argv, 8) == -1,
          "an unknown device is refused, not launched as something else");

    g.bsd = CONSOLE_BSD_USB;
    CHECK(console_neutrino_args(&g, tiny, sizeof tiny, argv, 8) == -1,
          "a command line that does not fit is refused, not truncated");
    CHECK(console_neutrino_args(&g, store, sizeof store, argv, 2) == -1,
          "too few argv slots is refused");
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
    test_scan();
    test_mock_sorted();
    printf("1..%d\n", checks);
    if (failures) {
        fprintf(stderr, "%d of %d checks failed\n", failures, checks);
        return 1;
    }
    return 0;
}
