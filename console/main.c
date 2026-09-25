/* The OPHTML console: any ps2ui theme, driven as a game launcher.
 *
 * It lists the ISOs on every drive it can mount -- USB, an exFAT
 * internal HDD, microSD over MX4SIO or MMCE -- through whatever UI the
 * theme draws, and hands the one you pick to Neutrino. The theme is a
 * .uib like any other; the only thing that makes it a console theme
 * is that it uses the names README.md lists (game-0, game-0-title,
 * sel-title, status, ...). A name the theme does not have is simply
 * not filled, so a theme can be as bare as one list of titles.
 *
 * THE BOOT, IN ORDER, AND WHY IT IS THIS ORDER:
 *
 *   1. GS up, a plain dark screen.
 *   2. IOP reset and every storage module loaded (storage.c).
 *   3. Wait for the drives to mount -- a USB stick takes a second or
 *      two -- still on the plain screen.
 *   4. Choose the theme: theme.uib beside the ELF, then OPHTML/theme.uib
 *      on each drive, then the one built in.
 *   5. Upload it once, and only then draw it.
 *   6. Scan each drive, drawing between them, and fill the list.
 *
 * The theme cannot be drawn before the drives are up because it may be
 * ON one of them, and it cannot be swapped once drawn because the
 * runtime uploads once and never releases VRAM (F19). So the plain
 * screen in 1-3 is the price of loading a theme off a USB stick, and it
 * lasts as long as the drives take to appear -- about three seconds.
 *
 * THE SCREEN IS THE ERROR CHANNEL, as in the starter: solid red means
 * even the built-in theme would not load (a build problem, not yours),
 * solid yellow means it did not fit in VRAM, solid grey means a
 * mandatory IOP module failed -- the ELF is broken or the console is
 * not a PS2 we understand. Grey, because every other colour is taken:
 * after a launch, PS2SDK's elf-loader paints its own progress in
 * nine of them (README.md), and a bench photo has to tell the two
 * apart. Everything recoverable goes to the theme's
 * `status` slot instead, in words. */

#include <kernel.h>
#include <malloc.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <gsKit.h>
#include <dmaKit.h>
#include <libpad.h>

#include "ps2ui.h"
#include "library.h"
#include "storage.h"
#include "scan.h"
#include "launch.h"

/* The built-in theme, examples/console, linked in by bin2c. */
extern unsigned char theme_uib[];
extern unsigned int size_theme_uib;

/* Enough for a large collection on a 2 TB drive, at ~470 bytes each. */
#define GAMES_MAX 1500

static GSGLOBAL *gs;
static ps2ui_ctx ui;
static ps2ui_list list;
static int rows;

static console_game games[GAMES_MAX];
static int n_games;
static console_device devs[CONSOLE_DEVICES_MAX];
static int n_devs;
static char launch_dir[CONSOLE_PATH_MAX];

#define BG GS_SETREG_RGBAQ(0x0a, 0x0e, 0x1a, 0x80, 0x00)

/* ---------------------------------------------------------------- GS */

static void hold(u8 r, u8 g, u8 b)
{
    for (;;) {
        gsKit_clear(gs, GS_SETREG_RGBAQ(r, g, b, 0x80, 0x00));
        gsKit_queue_exec(gs);
        gsKit_sync_flip(gs);
    }
}

/* A frame with no theme: steps 1-3 above. */
static void blank(void)
{
    gs->PrimAlphaEnable = GS_SETTING_OFF;
    gsKit_clear(gs, BG);
    gsKit_queue_exec(gs);
    gsKit_sync_flip(gs);
}

/* See the starter for why blending goes off across the clear. */
static void frame(void)
{
    gs->PrimAlphaEnable = GS_SETTING_OFF;
    gsKit_clear(gs, BG);
    gs->PrimAlphaEnable = GS_SETTING_ON;
    ps2ui_render(&ui, gs);
    gsKit_queue_exec(gs);
    gsKit_sync_flip(gs);
    gsKit_TexManager_nextFrame(gs);
}

static void gs_init(void)
{
    dmaKit_init(D_CTRL_RELE_OFF, D_CTRL_MFD_OFF, D_CTRL_STS_UNSPEC,
                D_CTRL_STD_OFF, D_CTRL_RCYC_8, 1 << DMA_CHANNEL_GIF);
    dmaKit_chan_init(DMA_CHANNEL_GIF);
    gs = gsKit_init_global();
    gs->PSM = GS_PSM_CT32;
    gs->PSMZ = GS_PSMZ_16S;
    gs->DoubleBuffering = GS_SETTING_ON;
    gs->ZBuffering = GS_SETTING_OFF;
    gsKit_init_screen(gs);
    gsKit_mode_switch(gs, GS_ONESHOT);
}

/* ------------------------------------------------------------- input */

static char pad_buf[256] __attribute__((aligned(64)));

/* freepad on the SDK's sio2man, both loaded by storage.c -- not the
 * ROM's PADMAN, which cannot share the bus with the card-slot drivers.
 * (A ROMPAD=1 build loads the ROM pair instead, for the emulator; the
 * libpad calls below are the same for both.) */
static void input_init(void)
{
    padInit(0);
    padPortOpen(0, 0, pad_buf);
}

static void input_end(void)
{
    padPortClose(0, 0);
    padEnd();
}

static unsigned input_edges(void)
{
    struct padButtonStatus b;
    static unsigned held = 0;
    unsigned now, edges;

    if (padGetState(0, 0) != PAD_STATE_STABLE) return 0;
    if (padRead(0, 0, &b) == 0) return 0;
    now = 0xffffu ^ (unsigned)b.btns; /* active low */
    edges = now & ~held;
    held = now;
    return edges;
}

/* ------------------------------------------------------------- theme */

static void *read_file(const char *path, size_t *len)
{
    int fd = open(path, O_RDONLY);
    off_t size;
    unsigned char *buf;
    size_t got = 0;

    if (fd < 0) return NULL;
    size = lseek(fd, 0, SEEK_END);
    /* A blob is a few hundred KiB. Refusing anything past 4 MiB keeps a
     * mis-named ISO from being read into memory as a theme. */
    if (size <= 0 || size > (4 << 20) || lseek(fd, 0, SEEK_SET) != 0) {
        close(fd);
        return NULL;
    }
    /* ps2ui points the GS straight into the blob, so it must be as
     * aligned as bin2c's arrays are. */
    buf = memalign(64, (size_t)size);
    while (buf && got < (size_t)size) {
        int r = read(fd, buf + got, (size_t)size - got);
        if (r <= 0) { free(buf); buf = NULL; break; }
        got += (size_t)r;
    }
    close(fd);
    *len = got;
    return buf;
}

static int load_blob(const void *blob, size_t len)
{
    size_t need = ps2ui_arena_size(blob, len);
    void *arena;

    if (need == 0) return PS2UI_ERR_MAGIC;
    arena = memalign(PS2UI_ARENA_ALIGN, need);
    if (arena == NULL) return PS2UI_ERR_ARENA;
    /* On refusal the arena is untouched and simply leaked: this runs at
     * most twice, at boot. */
    return ps2ui_load(&ui, blob, len, arena, need);
}

/* Step 4. Writes what happened to a refused theme into `note`, so the
 * status line can say why the built-in one is showing. */
static void choose_theme(char *note, size_t cap)
{
    char path[CONSOLE_PATH_MAX];
    int d, rc;
    size_t len = 0;
    void *blob = NULL;

    note[0] = '\0';
    if (launch_dir[0] &&
        (size_t)snprintf(path, sizeof path, "%stheme.uib", launch_dir) < sizeof path)
        blob = read_file(path, &len);
    for (d = 0; blob == NULL && d < n_devs; d++) {
        snprintf(path, sizeof path, "%s/OPHTML/theme.uib", devs[d].mount);
        blob = read_file(path, &len);
    }
    if (blob) {
        rc = load_blob(blob, len);
        if (rc == PS2UI_OK) return;
        snprintf(note, cap, "%s refused (%d); built-in theme", path, rc);
        free(blob);
    }
    if (load_blob(theme_uib, size_theme_uib) != PS2UI_OK)
        hold(0x80, 0x00, 0x00);
}

/* --------------------------------------------------------- the list */

static void status(const char *text)
{
    ps2ui_slot_set(&ui, "status", text);
}

static void set(const char *fmt, int row, const char *text)
{
    char name[40];
    snprintf(name, sizeof name, fmt, row);
    ps2ui_slot_set(&ui, name, text);
}

static const char *media(const console_game *g)
{
    return g->media == CONSOLE_MEDIA_CD ? "CD" : "DVD";
}

/* Refill every row from the list window, and the sel-* slots from the
 * selection. Cheap -- a slot_set is a strcmp walk and a copy -- so it
 * runs after anything that could have moved. */
static void fill(void)
{
    const console_game *sel = n_games ? &games[list.sel] : NULL;
    int r;

    for (r = 0; r < rows; r++) {
        int item = ps2ui_list_item_at(&list, (uint16_t)r);
        const console_game *g = item >= 0 ? &games[item] : NULL;
        set("game-%d-title", r, g ? g->title : "");
        set("game-%d-id", r, g ? g->id : "");
        set("game-%d-media", r, g ? media(g) : "");
        set("game-%d-device", r, g ? console_bsd_label((console_bsd)g->bsd) : "");
    }
    ps2ui_slot_set(&ui, "sel-title", sel ? sel->title : "");
    ps2ui_slot_set(&ui, "sel-id", sel ? sel->id : "");
    ps2ui_slot_set(&ui, "sel-media", sel ? media(sel) : "");
    ps2ui_slot_set(&ui, "sel-device",
                   sel ? console_bsd_label((console_bsd)sel->bsd) : "");
    ps2ui_list_apply_visibility(&ui, &list);
}

/* The row the focus is on, or -1 if it is on something else -- a
 * button the theme put beside the list, say. */
static int focused_row(void)
{
    const char *f = ps2ui_focus_name(&ui);
    int r = 0;

    if (f == NULL || strncmp(f, "game-", 5) != 0) return -1;
    for (f += 5; *f; f++) {
        if (*f < '0' || *f > '9') return -1;
        r = r * 10 + (*f - '0');
    }
    return r < rows ? r : -1;
}

/* A theme's rows are game-0, game-1, ... on its games screen, however
 * many it drew. Counted rather than declared, so a theme says how many
 * rows it has by having them. */
static int count_rows(void)
{
    char name[16];
    int r;
    for (r = 0; r < 256; r++) {
        snprintf(name, sizeof name, "game-%d", r);
        if (ps2ui_visible_get(&ui, name) == PS2UI_VISIBLE_UNKNOWN) break;
    }
    return r;
}

/* ------------------------------------------------------------- steps */

/* Step 3. Poll the mounts until they stop changing. A USB stick
 * appears one to three seconds after usbmass_bd loads, an HDD and an
 * MMCE almost at once, so when USB is up the wait gives it 2.5 s before
 * it will settle for what it has; the whole wait is capped at 5 s. */
static void wait_for_drives(int have)
{
    int f, last = -1, since = 0;
    int min = (have & CONSOLE_HAVE_USB) ? 150 : 30;

    for (f = 0; f < 300; f++) {
        blank();
        if (f % 15 == 0) {
            int n = console_storage_devices(devs, CONSOLE_DEVICES_MAX), i;
            if (n != last) { last = n; since = f; }
            for (i = 0; i < n; i++)
                if (devs[i].bsd == CONSOLE_BSD_USB) min = 30;
        }
        if (f >= min && last > 0 && f - since >= 60) break;
    }
    n_devs = console_storage_devices(devs, CONSOLE_DEVICES_MAX);
}

/* Step 6. */
static void scan_all(const char *note)
{
    char line[64], labels[40] = "";
    int d;

    for (d = 0; d < n_devs; d++) {
        const char *label = console_bsd_label(devs[d].bsd);
        snprintf(line, sizeof line, "Reading %s (%.7s)", label, devs[d].mount);
        status(line);
        frame();
        n_games = console_scan(devs[d].mount, devs[d].bsd, games, n_games,
                               GAMES_MAX);
        if (!strstr(labels, label)) {
            if (labels[0]) strcat(labels, ", ");
            strcat(labels, label);
        }
    }
    console_sort(games, (size_t)n_games);

    snprintf(line, sizeof line, n_games == 1 ? "%d game" : "%d games", n_games);
    ps2ui_slot_set(&ui, "game-count", line);

    if (note[0])
        status(note);
    else if (n_devs == 0)
        status("No drives found");
    else if (n_games == 0)
        status("No ISOs in DVD/ or CD/");
    else
        status(labels);
}

#ifdef CONSOLE_MOCK
/* `make MOCK=1`: the list mock_library.h describes, appended after the
 * scan found whatever it found (in the emulator, nothing). What this
 * build is for is in that header. */
static void add_mock(void)
{
    static const struct {
        const char *title, *id;
        int media, bsd;
    } mock[] = {
#define MOCK(t, i, m, b) { t, i, m, b },
#include "mock_library.h"
#undef MOCK
    };
    char line[32];
    unsigned k;

    for (k = 0; k < sizeof mock / sizeof mock[0] && n_games < GAMES_MAX; k++) {
        console_game *g = &games[n_games++];
        snprintf(g->path, sizeof g->path, "mock:/DVD/%s.iso", mock[k].title);
        snprintf(g->title, sizeof g->title, "%s", mock[k].title);
        snprintf(g->id, sizeof g->id, "%s", mock[k].id);
        g->media = (uint8_t)mock[k].media;
        g->bsd = (uint8_t)mock[k].bsd;
    }
    console_sort(games, (size_t)n_games);
    snprintf(line, sizeof line, "%d games", n_games);
    ps2ui_slot_set(&ui, "game-count", line);
    status(CONSOLE_MOCK_STATUS);
}
#endif

static void launch_selected(void)
{
    char path[CONSOLE_PATH_MAX], line[80];
    const console_game *g = &games[list.sel];
    int i, rc;

    if (!console_find_neutrino(launch_dir, devs, n_devs, path, sizeof path)) {
        status("Neutrino not found: put neutrino/ at a drive's root");
        return;
    }
    snprintf(line, sizeof line, "Starting %s", g->title);
    status(line);
    /* Two frames, so the line is on the displayed buffer and not only
     * the back one when the loader takes over the screen. */
    for (i = 0; i < 2; i++) frame();

    input_end();
    rc = console_launch(path, g);
    input_init();
    snprintf(line, sizeof line, "Could not start Neutrino (%d)", rc);
    status(line);
}

static void set_launch_dir(const char *argv0)
{
    const char *slash;
    size_t n;

    launch_dir[0] = '\0';
    if (argv0 == NULL) return;
    slash = strrchr(argv0, '/');
    if (slash == NULL) slash = strrchr(argv0, ':');
    if (slash == NULL) return;
    n = (size_t)(slash - argv0) + 1;
    if (n >= sizeof launch_dir) return;
    memcpy(launch_dir, argv0, n);
    launch_dir[n] = '\0';
}

/* MX4SIO is chosen, not detected (see storage.h): by a -mx4sio
 * argument, or by the ELF's name containing "m4s" -- the convention
 * NHDDL uses, for launchers that cannot pass arguments. */
static int wants_mx4sio(int argc, char *argv[])
{
    int i;
    const char *base;

    for (i = 1; i < argc; i++)
        if (strcmp(argv[i], "-mx4sio") == 0) return 1;
    if (argc < 1 || argv[0] == NULL) return 0;
    base = strrchr(argv[0], '/');
    base = base ? base + 1 : argv[0];
    return strstr(base, "m4s") != NULL || strstr(base, "M4S") != NULL;
}

int main(int argc, char *argv[])
{
    const char *failed = NULL;
    char note[CONSOLE_PATH_MAX + 32];
    int have;

    set_launch_dir(argc > 0 ? argv[0] : NULL);

    gs_init();
    blank();

    have = console_storage_start(wants_mx4sio(argc, argv), &failed);
    if (have < 0) hold(0x40, 0x40, 0x40);
    input_init();
    wait_for_drives(have);

    choose_theme(note, sizeof note);
    gs->PrimAlphaEnable = GS_SETTING_ON;
    if (ps2ui_upload(&ui, gs) != 0) hold(0x80, 0x80, 0x00);

    /* A theme with a screen called "games" is opened on it; otherwise
     * the list is wherever the theme starts. */
    ps2ui_screen_set(&ui, "games");
    rows = count_rows();
    ps2ui_list_init(&list, "game-", (uint16_t)rows);

    status("Looking for games");
    frame();
    scan_all(note);
#ifdef CONSOLE_MOCK
    add_mock();
#endif
    if (rows == 0 && n_games > 0)
        status("This theme has no game-0 row to list games in");

    ps2ui_list_set_count(&ui, &list, (uint16_t)n_games);
    fill();

    for (;;) {
        unsigned e = input_edges();
        int row = focused_row();

        if (e & (PAD_UP | PAD_DOWN)) {
            int d = (e & PAD_UP) ? -1 : 1;
            /* Up and down walk the list while focus is in it, and only
             * leave it -- to whatever the theme put above or below --
             * once the list is at its end. */
            if (row < 0 || !ps2ui_list_move(&ui, &list, d))
                ps2ui_move(&ui, d < 0 ? PS2UI_UP : PS2UI_DOWN);
        }
        if (e & PAD_LEFT)  ps2ui_move(&ui, PS2UI_LEFT);
        if (e & PAD_RIGHT) ps2ui_move(&ui, PS2UI_RIGHT);
        if (e & PAD_L1) ps2ui_list_move(&ui, &list, -rows);
        if (e & PAD_R1) ps2ui_list_move(&ui, &list, rows);

        /* Focus can arrive on a row by ps2ui_move -- from a button
         * beside the list -- without the list knowing. Make the
         * selection follow it, so the row that looks selected is the
         * one that launches. */
        row = focused_row();
        if (row >= 0 && ps2ui_list_item_at(&list, (uint16_t)row) >= 0 &&
            row != ps2ui_list_selected_row(&list))
            ps2ui_list_select(&ui, &list, (uint16_t)(list.top + row));

        if ((e & PAD_CROSS) && row >= 0 && n_games > 0)
            launch_selected();

        if (e) fill();
        frame();
    }
    return 0;
}
