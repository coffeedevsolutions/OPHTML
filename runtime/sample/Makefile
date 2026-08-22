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
