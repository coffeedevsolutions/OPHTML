# The OPHTML console

A PS2 program that turns any ps2ui theme into a game launcher. It finds
the ISOs on every drive it can mount, lists them through whatever UI
the theme draws, and hands the one you pick to
[Neutrino](https://github.com/rickgaiser/neutrino) to boot.

The theme is an ordinary `.uib` that uses some names this page defines.
You write HTML and CSS, `ps2ui build` it, copy `theme.uib` to a drive,
and the console runs your UI. Nothing in C is yours to write.

**Status: booted in an emulator, not yet on a console.**
- CI builds `ophtml.elf` in the ps2dev container and publishes it as
  the `ophtml-console-elf` artifact of `hw.yml`.
- `console/tests` runs the portable half (file names, ISO9660,
  SYSTEM.CNF, Neutrino's command line, the directory scan) on the host.
- `hw.yml` boots the MOCK build in the Play! emulator and diffs its
  frame against the previewer drawing the same games. That proves:
  - the IOP reset and all fourteen modules load;
  - the drive wait ends;
  - the built-in theme draws;
  - the list binds games to rows, labels and the selection panel.
- `hw.yml` also presses buttons at a navigation build in Play!: Down
  three times, then R1, then L1. It diffs each frame against the
  previewer replaying the same keys. That proves up/down, paging, the
  window scrolling and the selection panel following the highlight.
  It does **not** prove the pad driver: Play! only answers the ROM's
  pad modules, so that build loads those instead of `freepad` (see
  [Building](#building)). `freepad` is still bench case C8's.
- Play! has no USB, HDD or card slot. So nothing has mounted a real
  drive or started a game yet. That is what
  [the bench cases](#bench-cases) below are for, and each one is
  `[open]` until a sitting reports it.

## What goes on the drive

The layout is OPL's, so an existing OPL library works as it is:

```
<drive root>/
  DVD/                  Name.iso, or SLUS_200.02.Name.iso
  CD/                   the same, for CD games
  neutrino/             the Neutrino release folder, unzipped as-is
  OPHTML/theme.uib      optional: your theme
```

Put `ophtml.elf` wherever you launch programs from: a memory card
through FMCB or wLaunchELF, or a USB stick. A `theme.uib` beside the
ELF wins over one in `OPHTML/`, and with neither present the console
uses its built-in theme ([examples/console](../examples/console)).

**Neutrino is not included.** Get it from its releases page and unzip
its folder at a drive's root, or beside `ophtml.elf`. The console looks
in these places, in this order:
1. beside the ELF, as `neutrino/neutrino.elf` then `neutrino.elf`;
2. at each drive's root, as `neutrino/neutrino.elf`;
3. on a memory card, at `mc0:/APPS/neutrino/neutrino.elf` or the same
   path on `mc1:`.

This is NHDDL's search, less the devices the console does not mount.

## Drives

| Drive | How it is attached | Shown as | Neutrino |
|---|---|---|---|
| USB stick or USB SD reader | USB port, FAT32 or exFAT | `USB` | `-bsd=usb` |
| Internal HDD | expansion bay, **exFAT** (MBR or GPT) | `HDD` | `-bsd=ata` |
| microSD | MX4SIO adapter in a memory card slot | `SD` | `-bsd=mx4sio` |
| microSD | SD2PSX / MemCard PRO2 (MMCE) | `MMCE` | `-bsd=mmce` |

**MX4SIO is opt-in.** MX4SIO and MMCE both drive the memory card port,
and cannot both be loaded (storage.h has the detail). The console loads
MMCE by default. For MX4SIO, rename the ELF so its name contains `m4s`
(`ophtml-m4s.elf`), or pass it `-mx4sio`. This is NHDDL's convention.

**An APA-formatted HDD (HDLoader / HDL Batch Installer) is not read.**
Only exFAT is supported.

## The theme contract

The console looks up these names in your theme. **Every one is
optional.** A name your theme leaves out is simply never filled, so
one list of titles is already a working theme.

| Name | Kind | What the console puts there |
|---|---|---|
| `game-0` … `game-N` | focusable row (`data-repeat` + `id="game-{i}"`) | one game each. The console counts them, so your theme has as many rows as it draws |
| `game-{i}-title` | `data-slot` | the game's title, from its file name |
| `game-{i}-id` | `data-slot` | its title ID (`SLUS_200.02`), from the name or the disc |
| `game-{i}-media` | `data-slot` | `DVD` or `CD` |
| `game-{i}-device` | `data-slot` | `USB`, `HDD`, `SD` or `MMCE` |
| `sel-title`, `sel-id`, `sel-media`, `sel-device` | `data-slot` | the same four, for the selected game |
| `game-count` | `data-slot` | `12 games` |
| `status` | `data-slot` | what the console is doing, or what went wrong |

- **The screen.** If your theme has a screen named `games`, the console
  opens on it. Otherwise it opens on your theme's first screen.
- **Other elements.** Anything else in your theme is drawn exactly as
  you wrote it. Focusable elements that aren't rows are reachable with
  the D-pad in the usual way: left and right always move between
  elements, and up and down leave the list once it reaches its end.

[examples/console/ui/games.html](../examples/console/ui/games.html) is
the built-in theme and uses every name above.

### Checking and previewing your theme

`ps2ui check` (and `ps2ui-check`) holds any blob with a numbered
`game-N` row or `game-N-*` slot to the contract. (Not `sel-*` or
`status` alone: those are ordinary names other UIs use for their own
panels.) It is an **error** when the console would leave
something showing its placeholder:
- a gap in the rows (`game-0`, `game-1`, `game-3`: the console stops
  counting at `game-2`);
- rows on a screen the console never opens;
- a `game-N-*` slot for a row that doesn't exist.

It is a **warning** when:
- a name is one the console never fills (`game-0-titel` is reported
  with "did you mean 'title'?");
- a slot is too short for what the console writes (an ID is always 11
  characters);
- the rows have no title slot.

`ps2ui-check --console` runs these checks on a blob with no `game-N`
names.

`ps2ui serve --console` fills your theme with the mock games and drives
the list the way the console does: up and down walk it, and focus that
lands on a row pulls the selection with it. You see your theme with a
full library before it ever reaches a console.

## Controls

| Button | Does |
|---|---|
| Up / Down | move through the list (and out of it at either end) |
| L1 / R1 | a page up or down |
| Left / Right | move between the theme's other focusable elements |
| ✕ | start the selected game |

## What the screen says

Everything recoverable goes to the `status` slot, in words:
- `No drives found`;
- `No ISOs in DVD/ or CD/`;
- `Neutrino not found: put neutrino/ at a drive's root`;
- a `theme.uib` the runtime refused, with its error code, while the
  built-in theme shows instead.

Before the theme is up, the screen is the only channel:

| Screen | Meaning |
|---|---|
| plain dark, up to ~5 s | normal: the drives are mounting (a USB stick takes 1–3 s) |
| solid grey | a mandatory IOP module failed to load |
| solid red | the built-in theme did not load: the ELF is broken |
| solid yellow | the theme did not fit in VRAM |

Once ✕ is pressed, PS2SDK's elf-loader takes over and paints its own
progress. A launch that stops on one of these colours is the loader
talking, not the console:

| Colour | Meaning |
|---|---|
| magenta | `neutrino.elf` could not be loaded from its path |
| red | the loader was given bad arguments |
| green | stuck inside the IOP's load of `neutrino.elf` |
| purple, and it stays | the loader has jumped to Neutrino, and Neutrino stopped |

The loader's red comes after ✕; the console's own red and yellow come
before its theme ever draws, so the moment tells you whose it is. If the
screen goes on past purple to Neutrino's output, the console's part is
done.

## Building

```sh
./examples/console/build.sh          # the built-in theme
docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev \
    sh -c 'apk add --no-cache make && make -C console'
make -C console/tests test           # the host tests; needs only cc
```

`make -C console THEME=path/to/ui.uib` builds a different theme in as
the default.

`make -C console MOCK=1 EE_BIN=ophtml-mock.elf` lists
[mock_library.h](mock_library.h)'s fourteen invented games as if a
drive held them. Boot it in an emulator to see your theme filled
without a console. Put your blob in with `THEME=`.

`make -C console MOCK=1 ROMPAD=1 EE_BIN=ophtml-nav.elf` is the same
build on the ROM's pad modules (`rom0:SIO2MAN`, `rom0:PADMAN`) instead
of the SDK's `sio2man` and `freepad`. **It exists for Play!**, which
answers pad reads only through its stand-in for the ROM pair; measured,
Play! delivers no input to the SDK pad drivers after an IOP reset. The
ROM pair can't share the bus with the card-slot drivers, so this build
has no memory card, MMCE or MX4SIO. Never ship it: the real ELF uses
`freepad`, as NHDDL does on consoles.

## How it works

`main.c` explains the boot order and why it is fixed. In short:
1. The console resets the IOP and loads its own drivers. Whatever
   launched it reset the IOP too (F-030), so nothing is left over.
2. It waits for the drives to mount.
3. It chooses the theme. This has to come after step 2 because the
   theme may be on one of those drives. It uploads the theme once
   (F19), then scans.

The launch uses elf-loader's no-reset entry point together with
Neutrino's `-qb`. So Neutrino reads the game through the drivers the
console loaded: `launch.c` and `library.c` explain why that pairing is
the design and not a shortcut.

Credit where it is due: the module set, the MX4SIO/MMCE rule, the
`m4s` name convention and the `-qb` launch all come from
[NHDDL](https://github.com/pcm720/nhddl), which runs this path on
hardware every day.

## Bench cases

Each case is one sitting's worth: the setup, what to do, and what a
pass looks like. Report each as PASS / FAIL / VOID with a photo of the
screen, the way [docs/bench-phase1.md](../docs/bench-phase1.md) does.

| Case | Setup | Pass |
|---|---|---|
| C1 `[open]` | `ophtml.elf` on a memory card, no drives | the built-in theme draws within ~5 s; `status` reads `No drives found` |
| C2 `[open]` | a FAT32 or exFAT USB stick with `DVD/` holding two ISOs, one of them named `SLUS_xxx.xx.Name.iso` | both are listed in title order, with IDs; `status` reads `USB` |
| C3 `[open]` | C2 plus `neutrino/` on the stick | ✕ starts the selected game |
| C4 `[open]` | an exFAT HDD in the bay, with `DVD/` and `neutrino/` | the games are listed as `HDD`, and one boots |
| C5 `[open]` | a microSD card on MX4SIO, ELF renamed `ophtml-m4s.elf` | the games are listed as `SD`, and one boots |
| C6 `[open]` | a microSD card in an SD2PSX or MemCard PRO2 | the games are listed as `MMCE`, and one boots |
| C7 `[open]` | a `theme.uib` of your own beside the ELF | your theme draws, with the games filled in |
| C8 `[open]` | a pad | up/down/L1/R1 move the selection; the highlighted row is the one ✕ starts. The emulator has proven the navigation with the ROM pad driver; this case is what proves `freepad` |
