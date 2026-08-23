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
# `make PROBE6=1` builds the bring-up step 6 instrument: one texture
# drawn with each UV convention either side of an untextured reference
# of the same pattern, so the reading is which of two seams vanished.
# No .uib and no ps2ui involved -- it asks the GS directly.
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
# `make MODULATE=1` forces GSTEXTURE::Function to be set even where the
# GS_TFX_* macros are missing -- bring-up step 4's A/B. The container's
# gsKit lacks the macro, so ps2ui has been taking the untinted fallback
# in every build; this is the other arm of that.
ifdef MODULATE
EE_CFLAGS += -DPS2UI_GSKIT_HAS_FUNCTION=1
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

clean: objclean
	rm -f $(EE_BIN)

# Build products without the linked ELF, so two configurations can be
# built from one checkout without either deleting the other's output.
# `clean` cannot do this job: it removes $(EE_BIN), which defaults to
# the UI ELF, so cleaning between a STATIC build and a PROBE build
# silently threw away the first one.
objclean:
	rm -f $(EE_OBJS) ui_uib.c ps2ui.c ps2ui.h

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
