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

clean:
	rm -f $(EE_BIN) $(EE_OBJS) ui_uib.c ps2ui.c ps2ui.h

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
