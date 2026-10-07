/* A deliberately tiny launcher built on libophtml-console.a.
 *
 * Its only job is to prove the console core links against a `main` the
 * console's own Makefile did not build: it brings up storage, scans,
 * resolves and draws the built-in theme. It is compiled and
 * link-checked in CI, not booted (the PR for it says why). console/main.c
 * is the full-featured consumer -- input, paging, the launch handoff,
 * the status channel; this one leaves all of that out. It references
 * one symbol from each core object so the whole archive is exercised at
 * link:
 *
 *   console_storage_start / console_storage_devices   storage.o
 *   console_scan                                       scan.o
 *   console_sort / console_neutrino_args               library.o
 *   console_set_resolver / console_opl_resolver        library.o + resolver.o
 *   console_find_neutrino                              launch.o
 *
 * See console/README.md, "Building a launcher on the core", for the
 * link recipe this example follows.
 */

#include <kernel.h>
#include <malloc.h>
#include <gsKit.h>
#include <dmaKit.h>

#include "ophtml_console.h"
#include "ps2ui.h"

/* The theme, linked in by bin2c -- examples/console's built-in blob,
 * reused so this example bakes nothing of its own. */
extern unsigned char theme_uib[];
extern unsigned int size_theme_uib;

#define GAMES_MAX 64

static GSGLOBAL *gs;
static ps2ui_ctx ui;
static console_game games[GAMES_MAX];
static console_device devs[CONSOLE_DEVICES_MAX];

#define BG GS_SETREG_RGBAQ(0x0a, 0x0e, 0x1a, 0x80, 0x00)

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

/* Load the built-in theme into the runtime. The arena is leaked on a
 * refusal, which happens at most once, at boot. */
static int load_theme(void)
{
    size_t need = ps2ui_arena_size(theme_uib, size_theme_uib);
    void *arena;

    if (need == 0) return PS2UI_ERR_MAGIC;
    arena = memalign(PS2UI_ARENA_ALIGN, need);
    if (arena == NULL) return PS2UI_ERR_ARENA;
    return ps2ui_load(&ui, theme_uib, size_theme_uib, arena, need);
}

int main(int argc, char *argv[])
{
    const char *failed = NULL;
    char neutrino[CONSOLE_PATH_MAX];
    int n_devs, n_games = 0, i;

    (void)argc; (void)argv;

    /* The OPL CFG resolver, the console's default, so a game's
     * CFG/<ID>.cfg is applied. Registering it pulls resolver.o. */
    console_set_resolver(console_opl_resolver);

    gs_init();

    /* Bring up the IOP storage modules and scan every drive. In Play!
     * nothing mounts, which is fine: this example boots and draws
     * regardless, and a real drive is a bench concern. */
    console_storage_start(0, &failed);
    n_devs = console_storage_devices(devs, CONSOLE_DEVICES_MAX);
    for (i = 0; i < n_devs; i++)
        n_games = console_scan(devs[i].mount, devs[i].bsd, games, n_games,
                               GAMES_MAX);
    console_sort(games, (size_t)n_games);

    /* Resolve the first game and build its command line, so library.o's
     * arg builder and the resolver seam are referenced too. The result
     * is unused here -- this example never launches -- but the call
     * makes the link honest. */
    if (n_games > 0) {
        console_settings s;
        char store[CONSOLE_PATH_MAX * 3 + 128];
        char *av[8];
        console_resolve(&games[0], &s);
        console_neutrino_args(&games[0], &s, store, sizeof store, av, 8);
    }

    /* Reference launch.o without handing the machine away: find the
     * loader, do not start it. */
    console_find_neutrino("", devs, n_devs, neutrino, sizeof neutrino);

    if (load_theme() != PS2UI_OK) {
        for (;;) {
            gsKit_clear(gs, GS_SETREG_RGBAQ(0x80, 0x00, 0x00, 0x80, 0x00));
            gsKit_queue_exec(gs);
            gsKit_sync_flip(gs);
        }
    }
    gs->PrimAlphaEnable = GS_SETTING_ON;
    if (ps2ui_upload(&ui, gs) != 0) {
        for (;;) {
            gsKit_clear(gs, GS_SETREG_RGBAQ(0x80, 0x80, 0x00, 0x80, 0x00));
            gsKit_queue_exec(gs);
            gsKit_sync_flip(gs);
        }
    }

    for (;;) {
        gs->PrimAlphaEnable = GS_SETTING_OFF;
        gsKit_clear(gs, BG);
        gs->PrimAlphaEnable = GS_SETTING_ON;
        ps2ui_render(&ui, gs);
        gsKit_queue_exec(gs);
        gsKit_sync_flip(gs);
        gsKit_TexManager_nextFrame(gs);
    }
    return 0;
}
