---
id: runtime/deploying
title: Deploying
description: Get a built ELF onto a PlayStation 2, launch it, and read a full-screen colour as a status rather than a bug.
section: runtime
order: 47
version: 0.8.0
sources: [docs/deploying.md, tools/check-deploying.py, runtime/sample/main.c, runtime/sample/Makefile, .github/workflows/hw.yml]
---

# Deploying

## What it is

One file crosses from a build to a console. The baked `.uib` compiles into
the ELF with `bin2c`, so `ps2ui_sample.elf` needs no data file beside it and
touches no filesystem at runtime. Streamed textures are the exception:
filling a slot with `ps2ui_tex_set` reads bytes from `mass:/ps2ui/`, so a UI
that streams art needs USB attached. Convert the art on
[the host](page:runtime/streaming-art#converting-on-the-host) first.

Everything below a card or a launcher is described with one of two markers.

| marker | meaning |
|---|---|
| `[bench]` | Run on this project's own hardware. |
| `[practice]` | Standard PS2 homebrew procedure this project has not itself run. |

A `[practice]` step is not a guess. It has not gone through this
repository's own console, so treat a surprise there as a gap in this page
rather than a fault in the setup.

## Minimal example

Build inside a checkout against the toolchain, from a baked blob.

```sh
make -C runtime/sample UIB="$PWD/examples/channel6/build/ui.uib"
```

**Without a checkout**, `ps2ui vendor-runtime --starter src/` writes the
runtime and a buildable project beside it, and the copying, launching and
autoboot steps below apply from `src/` unchanged. See
[Starting from nothing](page:runtime/integrating#starting-from-nothing).
Two things do not carry over. Anything naming `runtime/sample/`,
`examples/channel6/build/ui.uib` or `tools/` is the checkout lane and has
no equivalent in an installed package. And the status-colour table below
is `runtime/sample/main.c`'s: the starter agrees on dark red and olive
and paints navy `#000080` where this one says magenta, which is not
the steel blue `#4080c0` in the table below, which
[first boot](page:runtime/first-boot) spells out.

The PS2 is a MIPS target, so a host compiler cannot produce this ELF.
[Integrating the runtime](page:runtime/integrating#minimal-example) covers
`ps2ui vendor-runtime` for a project outside this checkout; either way, the
compile runs inside the toolchain image.

```sh
docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make
```

The checkout command produces `runtime/sample/ps2ui_sample.elf`.

## Reference table

Four paths from that ELF onto a console.

| path | marker | steps |
|---|---|---|
| Memory card, multi-channel device | `[practice]` | Write the ELF into the channel image. Power on with the boot channel present. Switch to the target channel. Launch from `mc0:` in uLaunchELF. |
| Ordinary memory card | `[practice]` | Copy the ELF to the card with mymc++ or uLaunchELF. Launch from FMCB's menu or uLaunchELF. |
| USB | `[bench]` | Copy the ELF to a FAT32 stick. Launch from `mass:/` in uLaunchELF. |
| OPL apps list | `[practice]` | Add a line naming the ELF to `conf_apps.cfg`. Launch from OPL's own menu. |

A full-screen flat colour on any of these paths is a status, not a UI.
`runtime/sample/main.c` writes exactly four, plus a background that is not
one of them.

| screen colour | meaning |
|---|---|
| steel blue `#4080c0` | `minimal.elf` passed. Boot and video are fine. |
| dark red `#800000` | `ps2ui_load` failed. Re-read what the bake printed for the arena size. |
| olive `#808000` | `ps2ui_upload` failed. VRAM. |
| magenta `#ff00ff` | `SCREEN=` names a screen this blob does not have. |

Black is not a status. It is a boot failure rather than a runtime one, and
every fill above sits at Rec. 601 luma 30 or higher so none reads as black
on a dim panel.

## Behaviour

### Emulator

Play! runs the sample ELF headlessly in CI on every push and the frame is
image-diffed against the previewer's render. `[bench]` PCSX2 in
software-renderer mode is the closer stand-in short of a console, because
hardware renderers paper over exactly the GS behaviour worth testing.
`[practice]` Neither replaces a console: this project has found faults an
emulator did not surface.

### Card devices

A multi-channel device presents an 8 MB card image over the memory-card
port and executes nothing itself, so every pixel still comes from the GS.
On the microSD, a card is a directory and a channel is a file inside it,
eight channels per card by default. The device this project targets, and
the one [channel6](page:examples/channel6#source-tour) is named after, is
the PSxMemCard GEN2 running sd2psx or sd2psXtd firmware. An ordinary memory
card works the same way, without the channel switch: copy the ELF on and
launch it.

### Launching

FreeMcBoot patches the console's browser to add launch items, so an item in
the OSDSYS menu can point straight at the ELF's path. Under Open PS2
Loader, two things are worth separating: listing an existing ELF in OPL's
own menu through `conf_apps.cfg`, and building a UI shaped like OPL, which
is what the `examples/opl-env` example is for. A device in GameID mode
swaps cards on its own, watching for the ID OPL or UNIROM announces, so a
UI's channel can follow whichever game just launched.

### Autoboot

FreeMcBoot can launch an ELF at power-on instead of dropping to the
browser, configured in the same tool that sets the launch item. Bind a held
button to skip autoboot before relying on it: an ELF that crashes on load,
with nothing bound to bypass it, leaves a console that cannot reach a menu
without the card pulled and edited elsewhere. Get the ELF launching
manually first, confirm it draws and answers the D-pad, and only then bind
it to autoboot.

## Limits and errors

The bring-up matrix is complete on one console, an SCPH-50000 (NTSC)
booted from USB under FreeMcBoot.
[Steps 1 to 10](page:runtime/first-boot#steps-1-10) pass except step 8,
which is void on the bench panel because its deinterlacer weaves static
fields rather than showing the fault the step looks for.

The memory-card and autoboot paths above are `[practice]`, not `[bench]`.
They are how these devices are normally used, and the channel layout comes
from the device's own firmware, but this project has not run its own UI
through an autoboot slot on its bench console.

The status-fill table describes `runtime/sample/main.c` alone. A different
app draws whatever it draws on the same failures unless it copies the same
four `gsKit_clear` calls. If the screen shows something other than a flat
colour and still looks wrong, work
[the ten-step checklist](page:runtime/first-boot#steps-1-10) in order.

Read a status colour live, not from a photograph. A phone camera renders
saturated magenta as violet and lifts near-black toward maroon, so the hex
value a capture shows is not the hex the console wrote. What survives a
camera is the judgement the colours exist for, that the whole frame is one
flat colour and which one it is.

## Related pages

| page | why |
|---|---|
| [Integrating the runtime](page:runtime/integrating#minimal-example) | vendoring `ps2ui.c` and `ps2ui.h` outside this checkout, and the cross toolchain that produces the ELF |
| [First boot](page:runtime/first-boot#steps-1-10) | the ten-step checklist for a screen that is not one of the four flat colours |
| [Streaming art](page:runtime/streaming-art#converting-on-the-host) | converting art to texels and getting them onto the drive the USB path reads |
| [channel6](page:examples/channel6#source-tour) | the channel layout the multi-channel memory-card path is named after |
