/* A ps2ui starter: boot, load a baked blob, draw it, take input.
 *
 * `ps2ui vendor-runtime --starter <dir>` wrote this file next to
 * ps2ui.c and ps2ui.h. It is yours -- edit it, rename it, throw away
 * the half you do not need. Nothing in the toolchain reads it back.
 *
 * WHAT IT IS FOR. `pip install ophtml` gives you the whole authoring
 * path and then two C files, and between those two C files and a
 * console there is a gsKit context to bring up, a blob to link in, an
 * arena to size and a frame loop to write. None of that is ps2ui's
 * subject and all of it is in the way. This is the shortest correct
 * version of it.
 *
 * WHAT IS PROVEN AND WHAT IS NOT, because the difference matters more
 * than the line count:
 *
 *   - The init sequence, the load, the upload and the render loop are
 *     LIFTED FROM runtime/sample/main.c, which this project's CI boots
 *     in an emulator on every push and pixel-diffs against the host
 *     previewer's PNG. Every non-obvious line here -- blending off
 *     across the clear, Z off, the arena outliving the context -- is
 *     there because that sample proved it on a screen.
 *
 *     THIS FILE IS NOT ITSELF BOOTED BY ANYTHING YET. CI compiles it
 *     against the current ps2ui.h and links both its pad and no-pad
 *     builds in the ps2dev container, from an installed wheel. It is
 *     not captured and not diffed. Same code, different file is not
 *     the same as tested, and saying otherwise here would be the
 *     exact defect this project keeps finding in its own comments.
 *
 *     THE FIRST VERSION OF THIS PARAGRAPH WAS ITSELF THAT DEFECT. It
 *     said the file "cannot stop linking" -- in the run where the pad
 *     build did not link, because EE_LIBS was copied from a sample
 *     that names no libpad symbol and -lpad did not come with it. The
 *     job caught it; the sentence describing the job did not, having
 *     been written from what the job was supposed to say rather than
 *     from what it said. Read the run before believing this paragraph
 *     again.
 *
 *   - The pad section is compile-verified only. This repository owns
 *     no console and its bring-up sample deliberately loads no IOP
 *     service at all, so no test here has ever pressed a button. It
 *     is the standard ps2sdk idiom and it is the part to distrust
 *     first if the UI draws but will not move. `make NOPAD=1` builds
 *     with no IOP service at all and holds the baked focus, which is
 *     how you tell "the pad is wrong" from "the blob is wrong".
 *
 * THE SCREEN IS THE ERROR CHANNEL. There is no console on a console.
 * A solid colour is the whole diagnostic, and these three are the
 * same ones runtime/sample/main.c and docs/bringup.md already use:
 *
 *   solid red      ps2ui_load refused the blob (see the code below)
 *   solid yellow   ps2ui_upload could not fit the textures in VRAM
 *   solid blue     the named start screen is not in this blob
 *
 * Anything else on screen means the boot and video path work, which
 * is most of what can go wrong. */

#include <kernel.h>
#include <string.h>
#include <gsKit.h>
#include <dmaKit.h>

#include "ps2ui.h"

#ifndef PS2UI_STARTER_NOPAD
#include <libpad.h>
#include <loadfile.h>
#include <sifrpc.h>
#endif

/* Written by bin2c from your .uib at build time; the Makefile's
 * `UIB` variable says which blob. The names are bin2c's, derived
 * from the output file name, so renaming ui_uib.c renames these. */
extern unsigned char ui_uib[];
extern unsigned int size_ui_uib;

/* `make SCREEN=library` opens on a named screen instead of the one
 * the blob starts on. `ps2ui check` lists the names in yours. */

/* SIZE THIS FROM THE BAKE, NOT BY GUESSING. `ps2ui build` prints the
 * number on a line of its own:
 *
 *     ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] ...)
 *
 * 16 KiB is comfortably above what the shipped examples need. If it
 * is short, ps2ui_load returns PS2UI_ERR_ARENA and you get the red
 * screen rather than anything subtle -- the check below is what makes
 * this number safe rather than assumed.
 *
 * Static rather than malloc'd because that is the shape a PS2 app
 * wants, and because the context points INTO it: the arena has to
 * outlive every ps2ui_render, not just the load. A stack buffer in a
 * function that returns hands the GS a dangling CLUT pointer. */
#ifndef PS2UI_STARTER_ARENA
#define PS2UI_STARTER_ARENA (16 * 1024)
#endif

static ps2ui_ctx ui;
static uint8_t arena[PS2UI_STARTER_ARENA]
    __attribute__((aligned(PS2UI_ARENA_ALIGN)));

/* Hold one colour forever. Every caller of this has already decided
 * nothing better can happen. */
static void die(GSGLOBAL *gs, u8 r, u8 g, u8 b)
{
    for (;;) {
        gsKit_clear(gs, GS_SETREG_RGBAQ(r, g, b, 0x80, 0x00));
        gsKit_queue_exec(gs);
        gsKit_sync_flip(gs);
    }
}

/* ------------------------------------------------------------------
 * Input
 *
 * One function, one contract: return the buttons pressed SINCE THE
 * LAST CALL, as a mask of the PAD_* bits in libpad.h. Edge-triggered,
 * not level -- a UI that moves once per press is the whole point, and
 * doing it here keeps the frame loop below free of debounce.
 *
 * Swap this out for your own input source and nothing else changes.
 * ------------------------------------------------------------------ */

#ifdef PS2UI_STARTER_NOPAD

/* No IOP services at all, and no input: the UI comes up on the focus
 * the blob was baked with and stays there.
 *
 * HOLDING RATHER THAN CYCLING IS THE POINT. A build that moves on a
 * timer shows a different frame depending on when you look at it,
 * which is exactly what you do not want from the build whose job is
 * "does this draw at all". Held, the frame is the one `ps2ui build`
 * already wrote to build/preview.png, so a photograph or a capture
 * can be compared against it directly by eye or by
 * tools/framediff.py. */
static unsigned input_edges(void) { return 0u; }

static void input_init(void) {}

#else

static char pad_buf[256] __attribute__((aligned(64)));

static void input_init(void)
{
    /* These two are on every console's ROM, so there is nothing to
     * ship and nothing to find on a memory card. A launcher that used
     * LoadExecPS2 has already reset the IOP, which is why they are
     * loaded here rather than assumed. */
    SifInitRpc(0);
    SifLoadModule("rom0:SIO2MAN", 0, NULL);
    SifLoadModule("rom0:PADMAN", 0, NULL);

    padInit(0);
    padPortOpen(0, 0, pad_buf);
    /* Deliberately not blocking on PAD_STATE_STABLE here: a console
     * with no controller plugged in would never leave this function,
     * and a UI that draws is more useful than one that waits. The
     * read below simply reports nothing until the pad settles. */
}

static unsigned input_edges(void)
{
    struct padButtonStatus b;
    static unsigned held = 0;
    unsigned now, edges;

    if (padGetState(0, 0) != PAD_STATE_STABLE) return 0;
    if (padRead(0, 0, &b) == 0) return 0;

    /* libpad reports buttons ACTIVE LOW: a set bit means released.
     * Getting this backwards gives a UI that scrolls continuously the
     * moment it boots and stops when you touch it. */
    now = 0xffffu ^ (unsigned)b.btns;
    edges = now & ~held;
    held = now;
    return edges;
}

#endif

/* PAD_* are libpad's, and the NOPAD build has no libpad. Naming the
 * two bits it uses keeps the frame loop identical either way. */
#ifdef PS2UI_STARTER_NOPAD
#define PAD_UP     0x1000
#define PAD_RIGHT  0x2000
#define PAD_DOWN   0x4000
#define PAD_LEFT   0x8000
#define PAD_CROSS  0x0040
#endif

int main(void)
{
    GSGLOBAL *gs;
    int rc;

    dmaKit_init(D_CTRL_RELE_OFF, D_CTRL_MFD_OFF, D_CTRL_STS_UNSPEC,
                D_CTRL_STD_OFF, D_CTRL_RCYC_8, 1 << DMA_CHANNEL_GIF);
    dmaKit_chan_init(DMA_CHANNEL_GIF);

    gs = gsKit_init_global();
    gs->PSM  = GS_PSM_CT32;
    gs->PSMZ = GS_PSMZ_16S;
    gs->DoubleBuffering = GS_SETTING_ON;
    /* OFF, and not an oversight: ps2ui paints strictly back to front,
     * so a Z buffer would only cost VRAM and reorder nothing. */
    gs->ZBuffering = GS_SETTING_OFF;
    gsKit_init_screen(gs);
    gsKit_mode_switch(gs, GS_ONESHOT);

    /* ps2ui blobs carry GS-domain alpha, and the standard blend
     * equation (Cs - Cd) * As >> 7 + Cd is exactly what the baker
     * assumed when it quantised them. Leave this ON or every
     * translucent panel comes out opaque. */
    gs->PrimAlphaEnable = GS_SETTING_ON;

    rc = ps2ui_load(&ui, ui_uib, size_ui_uib, arena, sizeof arena);
    if (rc != PS2UI_OK) {
        /* rc says which: PS2UI_ERR_ARENA means raise
         * PS2UI_STARTER_ARENA to the number the bake printed;
         * PS2UI_ERR_VERSION means this ps2ui.c and this blob came
         * from different installs, which `ps2ui vendor-runtime` is
         * there to prevent; the rest are in ps2ui.h. On a desk,
         * `ps2ui check` gives you the same verdict in words. */
        die(gs, 0x80, 0x00, 0x00);
    }

    if (ps2ui_upload(&ui, gs) != 0) {
        /* The textures did not fit. `ps2ui build` prints the VRAM
         * budget it assumed and what the blob spends against it. */
        die(gs, 0x80, 0x80, 0x00);
    }

#ifdef PS2UI_STARTER_SCREEN
    if (!ps2ui_screen_set(&ui, PS2UI_STARTER_SCREEN)) {
        /* Named a screen this blob does not have. Blue rather than a
         * silent fall back to screen 0, which would look like the
         * SCREEN= flag being ignored. */
        die(gs, 0x00, 0x00, 0x80);
    }
#endif

    input_init();

    for (;;) {
        unsigned e = input_edges();

        if (e & PAD_UP)    ps2ui_move(&ui, PS2UI_UP);
        if (e & PAD_DOWN)  ps2ui_move(&ui, PS2UI_DOWN);
        if (e & PAD_LEFT)  ps2ui_move(&ui, PS2UI_LEFT);
        if (e & PAD_RIGHT) ps2ui_move(&ui, PS2UI_RIGHT);

        if (e & PAD_CROSS) {
            /* WHERE YOUR APPLICATION GOES. ps2ui_focus_name returns
             * the id you wrote in the HTML, so the UI and the code
             * agree on one vocabulary and neither owns an index:
             *
             *     const char *who = ps2ui_focus_name(&ui);
             *     if (!strcmp(who, "play")) launch_selected();
             *
             * ps2ui shows things; it does not know what they mean.
             * Data, device I/O and what a button does are yours --
             * ps2ui_slot_set puts your strings into the UI and
             * ps2ui_screen_set moves between screens. */
        }

        /* ps2ui_render does NOT clear. Clearing here rather than
         * inside it is what lets a dialog screen draw over whatever
         * is already in the buffer: render the background screen,
         * then the overlay, then flip.
         *
         * BLENDING OFF ACROSS THE CLEAR, AND BACK ON AFTER. This is
         * load-bearing, not tidiness. With it left on, the clear
         * composites through whatever ALPHA is currently set -- and on
         * the very first frame that is still gsKit's inverted default,
         * where 0x80 resolves to the DESTINATION and paints the
         * previous framebuffer instead of your background colour.
         * From frame two it would come out right by inheriting the
         * equation ps2ui_render asserted last time, which is a worse
         * kind of correct: right only because something else ran
         * first. A background clear has nothing to blend against. */
        gs->PrimAlphaEnable = GS_SETTING_OFF;
        gsKit_clear(gs, GS_SETREG_RGBAQ(0x0a, 0x0e, 0x1a, 0x80, 0x00));
        gs->PrimAlphaEnable = GS_SETTING_ON;

        ps2ui_render(&ui, gs);
        gsKit_queue_exec(gs);
        gsKit_sync_flip(gs);

        /* Age the texture manager's use counts once per frame, the way
         * Open-PS2-Loader's loop does. With a static UI it changes
         * nothing -- every texture is re-bound every frame, so nothing
         * ever looks evictable -- but a host streaming its own
         * textures through the same manager needs the counters
         * honest. */
        gsKit_TexManager_nextFrame(gs);
    }

    return 0;
}
