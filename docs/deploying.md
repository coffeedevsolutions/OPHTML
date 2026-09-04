# Getting a ps2ui UI onto a PlayStation 2

This is the path from a built blob to a UI running on real hardware. It
covers memory cards (including the multi-channel devices most homebrew
setups use now), Open PS2 Loader, and starting your UI automatically at
power-on.

**How to read the claims in this file.** This project distinguishes what
it has measured from what it has not, so each path below carries one of
two markers:

| marker | meaning |
|---|---|
| **[bench]** | done on the project's own hardware and written up in [bringup.md](bringup.md) |
| **[practice]** | standard PS2 homebrew procedure that this project has not itself executed |

A **[practice]** step is not a guess, but it has not been through this
repository's own console, so treat a surprise there as a gap in this
document rather than a fault in your setup, and please report it.

---

## What you are actually copying

One file. The baked `.uib` is compiled into the ELF by `bin2c` at build
time, so `ps2ui_sample.elf` is self-contained: it needs no data file
beside it and touches no filesystem at runtime. That matters on a
memory-card device, where you may have exactly one card slot and the
device is already in it.

The one exception is **streamed textures**. If your UI fills texture
slots at runtime with `ps2ui_tex_set`, those bytes are read from
`mass:/ps2ui/` and you need USB attached. Everything else, including all
text, chrome and theming, is inside the ELF.

---

## Try it in an emulator first

Cheaper loop, and it isolates whether a problem is your UI or your
console setup.

- **Play!** needs no BIOS, which makes it the fastest thing to reach.
  This repository's CI boots the sample ELF in Play! headlessly on every
  push and image-diffs the frame against the previewer, so it is a known
  quantity. **[bench]**
- **PCSX2 in software-renderer mode** is the most trustworthy stand-in
  short of the console, because the hardware renderers paper over exactly
  the GS behaviour you want to be testing. **[practice]**

Neither replaces a console. [bringup.md](bringup.md) records a fault
(alpha running exactly inverted) that existed from the renderer's first
line and that only hardware surfaced.

---

## 1. Bake the blob

```sh
./examples/channel6/build.sh        # or memcard, or opl-env, or your own
```

Read the two lines it prints about the arena and the tables. The arena
size is the buffer `ps2ui_load` is handed, and the build fails until it
is right.

## 2. Build the ELF

Needs the [ps2dev toolchain](https://github.com/ps2dev/ps2dev); CI uses
the `ghcr.io/ps2dev/ps2dev` container.

```sh
make -C runtime/sample UIB="$PWD/examples/channel6/build/ui.uib"
```

That produces `runtime/sample/ps2ui_sample.elf`. Useful variants:

- `MINIMAL=1` builds bring-up step 1 alone (clear, hold, exit). If
  nothing appears on screen, this tells you whether the boot path or the
  drawing failed, which is the first question worth answering.
- `STATIC=1` holds the baked initial focus instead of cycling through
  focus states on a timer.
- `SCREEN=probe` opens on a named screen. The sample walks focus but
  never switches screens, so without this a blob's later screens cannot
  be reached on a console at all.

## 3. Get it onto the console

### Option A: a memory card, on a multi-channel device

This is the setup the project targets, and the one `examples/channel6`
is named after.

The **PSxMemCard GEN2** is BitFunX's build of the open-source
[sd2psx](https://sd2psx.net/) card emulator, running sd2psx or
[sd2psXtd](https://sd2psxtd.github.io/) firmware. On the microSD, a card
is a directory and a channel is a file inside it:

```
MemoryCards/PS2/Card1/Card1-6.mcd     <- channel 6 of card 1
MemoryCards/PS2/BOOT/BootCard-1.mcd   <- the boot channel, where FMCB lives
```

Eight channels per card by default, set by `MaxChannels` in `CardX.ini`,
which also names them. You switch channels with BT1/BT2 on the device's
OLED.

The device presents an 8 MB card image to the console over the
memory-card port and executes nothing itself, so every pixel still comes
from the PS2's Graphics Synthesizer. "Running on channel 6" means the ELF
lives inside `Card1-6.mcd` and the PS2 boots it from `mc0:`.

To install: **[practice]**

1. Write `ps2ui_sample.elf` into the channel image. It is an ordinary PS2
   card image, so the usual tools work: mymc++ against the `.mcd`
   directly on your computer, or uLaunchELF on the console copying from
   USB with the device switched to that channel.
2. Power on with the **boot channel** presented, so FMCB or FunTuna comes
   up. The console boots whatever channel was present at power-on, and
   the boot channel is the one carrying the exploit.
3. **Then** switch to your channel with BT1/BT2.
4. Launch the ELF from `mc0:` in uLaunchELF.

The ordering in steps 2 and 3 is the part people get wrong. Switching
before boot means the console tries to boot a channel with no exploit on
it.

### Option B: an ordinary memory card

Same idea without the channel switching. Copy the ELF to the card with
mymc++ or uLaunchELF, put it somewhere you will find it (`mc0:/APPS/` is
a common convention), and launch it from FMCB's menu or uLaunchELF.
**[practice]**

### Option C: USB

What the project's own bench runs use: an SCPH-50000 booted from USB
under FreeMcBoot. Copy the ELF to a FAT32 stick, launch it from
uLaunchELF at `mass:/`. **[bench]**

This is the best iteration loop because replacing the ELF is a file copy
rather than a card write, and it is required anyway if your UI uses
streamed textures from `mass:/ps2ui/`.

---

## 4. Launching

### From FreeMcBoot

FMCB patches the console's browser to add launch items, so your ELF can
be started from the machine's own menu without a file manager in between.
Point an OSDSYS item at the ELF's path (`mc0:/APPS/ps2ui_sample.elf`, or
wherever you put it) using the FMCB configurator. **[practice]**

### Under Open PS2 Loader

OPL is worth treating as a first-class host rather than just a game
launcher, and `examples/opl-env` exists because an OPL-class browser is
the shape most people want.

Two different things you might mean: **[practice]**

- **Launching your UI from OPL.** OPL can list and start ELFs through its
  apps support, configured in `conf_apps.cfg`. Add a line naming your ELF
  and it appears in OPL's own menu.
- **Building a UI that behaves like OPL.** That is what `examples/opl-env`
  is: a six-screen environment with a windowed library, filters, a detail
  view and a confirm dialog. Copy it and replace the markup.

If your device supports GameID mode, the firmware watches for the ID that
OPL or UNIROM announces and swaps cards by itself, which means your UI's
channel can follow the game being launched.

---

## 5. Starting automatically at power-on

Two layers, and it helps to be clear about which one you are configuring.
**[practice]**

**FMCB's autoboot.** FreeMcBoot can launch an ELF at power-on instead of
dropping to the browser. In the FMCB configurator this is the default
action, pointed at your ELF's path. The console then comes straight up
into your UI.

**Keeping a way out.** Configure a held button to skip autoboot before
you rely on it. An ELF that crashes on load, with nothing bound to bypass
it, means a console that will not reach a menu, and recovering from that
needs the card pulled and edited elsewhere. Test the escape route first,
while you still have a working browser.

**Order of operations that works:** get the UI launching manually from
uLaunchELF, confirm it draws and responds to the D-pad, and only then
bind it to autoboot. Autoboot is a convenience, not a debugging
environment.

---

## If the screen is one flat colour

A full-screen flat colour is always a status, never a UI. Four exist and
they are readable across every ELF this project ships: **[bench]**

| fill | means |
|---|---|
| steel blue `#4080c0` | `minimal.elf` passed. Boot and video are fine |
| dark red `#800000` | `ps2ui_load` failed. Usually the arena, so re-read what the bake printed |
| olive `#808000` | `ps2ui_upload` failed. VRAM |
| magenta `#ff00ff` | `SCREEN=` names a screen this blob does not have |

**Black is not in that table on purpose.** Black is no picture, which is
a boot failure rather than a runtime one, and it is why none of the four
status colours may be dark.

Read these live rather than from a photograph. A phone renders saturated
magenta as violet and lifts near-black to maroon, so the hex you capture
is not the hex the console output. What survives a camera is the
judgement the colours are actually for: the whole frame is one flat
colour, and it is this one rather than that one.

If you see something other than a flat colour and it still looks wrong,
work [bringup.md](bringup.md) in order. Each of its ten steps isolates one
subsystem, and `examples/channel6`'s `probe` screen was built to give
every one of them something to look at.

---

## What has actually been verified

Being precise about this, because the difference matters when something
does not work:

- The **bring-up matrix is complete on a real PlayStation 2**, an
  SCPH-50000 (NTSC) booted from USB under FreeMcBoot. Steps 1 to 7, 9 and
  10 pass, including the full memcard UI rendering with legible text.
- **Step 8 (interlace field order) is void** on the bench panel, whose
  deinterlacer weaves static fields. The project is not held up on it.
- **The memory-card and autoboot paths above are [practice]**, not
  [bench]. They are how these devices are normally used, and the channel
  layout is documented from the device's own firmware, but this project
  has not run its own UI through an autoboot slot.

[bringup.md](bringup.md) is the hardware log, including the faults found
and what each one looked like before it was understood.
