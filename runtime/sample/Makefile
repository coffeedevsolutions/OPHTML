# PS2SDK build for the bring-up sample ELF. Requires the ps2dev
# toolchain (https://github.com/ps2dev/ps2dev; CI uses the
# ghcr.io/ps2dev/ps2dev container) and a baked blob:
#
#   ../../examples/memcard/build.sh          # produces ui.uib
#   make -C runtime/sample                   # produces ps2ui_sample.elf

EE_BIN  = ps2ui_sample.elf
EE_OBJS = main.o ps2ui.o ui_uib.o
EE_LIBS = -lgskit -ldmakit
# gsKit installs under $PS2DEV/gsKit in the ps2dev toolchain image,
# not inside $PS2SDK/ports.
EE_CFLAGS += -std=c99 -Wall -Werror -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
# `make STATIC=1` holds the baked initial focus instead of cycling, so a
# timed screenshot always catches the same frame the previewer renders.
ifdef STATIC
EE_CFLAGS += -DPS2UI_SAMPLE_STATIC
endif
# `make PROBE=1` builds the bring-up step 2 instrument instead of the UI:
# four solid-fill cases in colours no example uses, so a capture names
# which primitive paths draw. No .uib is involved.
# `make TELEMETRY=1` adds the once-a-second stats line on stdout; see
# main.c. Combines with the cycling default (a static build has nothing
# interesting to time).
ifdef TELEMETRY
EE_CFLAGS += -DPS2UI_SAMPLE_TELEMETRY
endif
# `make MINIMAL=1` builds bring-up step 1 alone: clear, hold, exit.
# The smallest thing that can prove the boot and video path.
ifdef MINIMAL
EE_CFLAGS += -DPS2UI_SAMPLE_MINIMAL
endif
ifdef PROBE
EE_CFLAGS += -DPS2UI_SAMPLE_PROBE
endif
# `make PROBE6=1` builds the bring-up step 6b instrument: seven columns
# over an aperiodic bar pattern, one variable per column, each above an
# untextured reference of itself; the reading is which column's seam is
# visible. No .uib, and no ps2ui except column G, which builds its
# palette through the runtime's CLUT convention -- pair it with
# LINEAR_CLUT=1 (probe6-linear.elf in CI) for the machine-readable A/B
# on the convention itself.
ifdef PROBE6
EE_CFLAGS += -DPS2UI_SAMPLE_PROBE6
endif
# `make SCREEN=probe` opens on the named screen rather than screen 0.
# The sample walks focus but never switches screens, so without this a
# blob's later screens cannot be reached on a console at all -- see the
# PS2UI_SAMPLE_SCREEN block in main.c. A name absent from the blob
# holds solid blue rather than falling back to screen 0.
ifdef SCREEN
EE_CFLAGS += -DPS2UI_SAMPLE_SCREEN='"$(SCREEN)"'
endif
# `make LINEAR_CLUT=1` uploads CLUTs unpermuted. The pair of ELFs is
# bring-up step 3's A/B: the CSM1 permutation is an involution, so
# "not applied" and "applied twice" are the same picture, and only a
# side-by-side says which side of it this build is on.
ifdef LINEAR_CLUT
EE_CFLAGS += -DPS2UI_CLUT_PERMUTE=0
endif
# `make LADDER=1` builds the height ladder: twelve rungs, three arms
# each, asking one question three ways -- is the bright bottom line
# there? Arm A is a textured quad with the UVs ps2ui ships, arm B is
# the same rung built from stacked 1px untextured quads, arm C is
# arm A with a +0.5 texel bias. No blob and no ps2ui in the path, for
# probe6's reason: the question is what the GS does with a textured
# sprite, so adding the runtime would add a variable.
ifdef OPLENV
EE_CFLAGS += -DPS2UI_SAMPLE_OPLENV
endif

ifdef LADDER2
EE_CFLAGS += -DPS2UI_SAMPLE_LADDER2
endif

ifdef LADDER
EE_CFLAGS += -DPS2UI_SAMPLE_LADDER
endif
# `make PROGRESSIVE=1` outputs 480p instead of 480i. The bench's
# baseline-row discriminator: the host previewer and the emulator both
# render full glyphs from the same command stream, so a console that
# clips them is either the display path or GS behaviour the emulator
# does not model. Progressive separates those in one boot and changes
# nothing else. Needs a television that syncs at 480p; if it does not,
# there is no picture and the reading simply did not happen.
ifdef PROGRESSIVE
EE_CFLAGS += -DPS2UI_SAMPLE_PROGRESSIVE
endif
# `make COVERS=1` builds the Phase 1 streaming bench: four 128x128
# streamed slots filled at runtime from mass:/ps2ui/cover*.raw, a
# four-phase loop (fill, swap, restore, composite) and an on-screen
# state line so a photograph labels itself. Pair it with
# UIB=../../fixtures/bench-stream/build/bench.uib -- the memcard blob
# has no streamed slots and the ELF would have nothing to fill.
ifdef COVERS
EE_CFLAGS += -DPS2UI_SAMPLE_COVERS
endif
# `make USB=1` (with COVERS=1) embeds the IOP mass-storage modules and
# brings them up itself. The first bench sitting reported
# `open cover0: -1` from a stick whose files were byte-exact: wLaunchELF
# launches via LoadExecPS2, which resets the IOP, so the launcher's own
# USB drivers are gone before this ELF runs. Nothing survives a reset;
# the ELF has to carry them.
#
# SEPARATE FROM COVERS, deliberately, so the host and the container
# compile the same thing for the same flag. `make syntax-check` builds
# COVERS without USB, because sifrpc.h and friends do not exist on the
# host -- and after the fileio.h episode this tree does not write a
# shim to pretend otherwise. The elf job is the arbiter for this path;
# see runtime/vendor/README.md.
ifdef USB
EE_CFLAGS += -DPS2UI_SAMPLE_USB
EE_OBJS   += irx_table.o
EE_LIBS   += -lpatches
endif
# `make NO_SYNC=1` removes the cache writeback from ps2ui_tex_set --
# the bench's falsification arm, in the same spirit as NO_ALPHA and
# LINEAR_CLUT. The EE writes texels through a write-back cache the GIF
# cannot see, so without the writeback the GS DMAs whatever was in RAM
# at that address. It is a picture of the fault, not a test of it, and
# it exists so the bench knows what a live cache fault looks like
# rather than guessing when a cover comes out wrong.
ifdef NO_SYNC
EE_CFLAGS += -DPS2UI_SKIP_SYNCDCACHE
endif
# `make NO_ALPHA=1` makes ps2ui_render assert PrimAlphaEnable OFF
# instead of ON -- bring-up step 4b's reference arm. gsKit feeds that
# field to TEX0.TCC, so this is what the grid looks like when the GS is
# told the glyph atlas has no alpha channel. It is a picture of the
# fault, not a test of it: nothing in the shipped path sets this.
ifdef NO_ALPHA
EE_CFLAGS += -DPS2UI_PRIMALPHA_OFF
endif
EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib

UIB = ../../examples/memcard/build/ui.uib

all: $(EE_BIN)

# Copy the runtime sources next to main.c so PS2SDK's implicit %.o
# rule builds them with its full include set (a custom compile rule
# here misses tamtypes.h and friends from ee/include).
ps2ui.c: ../ps2ui.c ../ps2ui.h
	cp ../ps2ui.h ps2ui.h
	cp ../ps2ui.c ps2ui.c

ps2ui.o: ps2ui.c

ui_uib.c: $(UIB)
	$(PS2SDK)/bin/bin2c $(UIB) ui_uib.c ui_uib

# The IOP modules, discovered rather than pinned: which set exists
# depends on the PS2SDK vintage and both present `mass:`. embed_irx.sh
# picks whichever is complete and names it in irx_stack_name, so a
# failure at the bench says which stack it was.
ifdef USB
irx_table.c irx_table.h: embed_irx.sh
	sh embed_irx.sh .
irx_table.o: irx_table.c irx_table.h
main.o: irx_table.h
endif

clean: objclean
	rm -f $(EE_BIN)

# Build products without the linked ELF, so two configurations can be
# built from one checkout without either deleting the other's output.
# `clean` cannot do this job: it removes $(EE_BIN), which defaults to
# the UI ELF, so cleaning between a STATIC build and a PROBE build
# silently threw away the first one.
objclean:
	rm -f $(EE_OBJS) ui_uib.c ps2ui.c ps2ui.h irx_*.c irx_table.h

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
