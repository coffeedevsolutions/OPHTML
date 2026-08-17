# PS2SDK build for the bring-up sample ELF. Requires the ps2dev
# toolchain (https://github.com/ps2dev/ps2dev; CI uses the
# ghcr.io/ps2dev/ps2dev container) and a baked blob:
#
#   ../../examples/memcard/build.sh          # produces ui.uib
#   make -C runtime/sample                   # produces ps2ui_sample.elf

EE_BIN  = ps2ui_sample.elf
EE_OBJS = main.o ps2ui.o ui_uib.o
EE_LIBS = -lgskit -ldmakit
EE_CFLAGS += -std=c99 -Wall -Werror -I$(PS2SDK)/ports/include
EE_LDFLAGS += -L$(PS2SDK)/ports/lib

UIB = ../../examples/memcard/build/ui.uib

all: $(EE_BIN)

ps2ui.o: ../ps2ui.c ../ps2ui.h
	$(EE_CC) $(EE_CFLAGS) -c $< -o $@

ui_uib.c: $(UIB)
	$(PS2SDK)/bin/bin2c $(UIB) ui_uib.c ui_uib

clean:
	rm -f $(EE_BIN) $(EE_OBJS) ui_uib.c

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
