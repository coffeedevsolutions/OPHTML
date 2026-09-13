# A ps2ui starter build. `ps2ui vendor-runtime --starter <dir>` wrote
# this next to main.c, ps2ui.c and ps2ui.h.
#
#   make UIB=build/ui.uib          # link that blob in and build the ELF
#   make NOPAD=1                   # no IOP services; holds the baked focus
#   make SCREEN=library            # open on a named screen
#   make clean
#
# THE PS2 IS A MIPS TARGET AND YOUR MACHINE IS NOT. This needs the
# ps2dev cross-toolchain (https://github.com/ps2dev/ps2dev), which is
# also what this project's CI uses. With Docker and nothing installed:
#
#   docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev make
#
# The blob is linked into the ELF rather than loaded at runtime, so
# there is one file to copy to a memory card and no path to get wrong.
# Re-bake and re-make to change the UI.

EE_BIN = ps2ui_app.elf

# Your .uib. `ps2ui build` writes it; the default is where a project
# created by `ps2ui` puts it.
UIB ?= build/ui.uib

EE_OBJS = main.o ps2ui.o ui_uib.o

# THESE THREE LINES ARE THE WHOLE INTEGRATION, and the reason this
# file exists rather than a paragraph telling you to write it. The
# ps2dev image ships gsKit under $PS2DEV/gsKit and does NOT put it on
# the include path, so without them ps2ui.c cannot find <gsKit.h> and
# the error names a missing header rather than a missing -I.
#
# The markers are not decoration: `ps2ui vendor-runtime` without
# --starter prints these lines for somebody adding ps2ui to an app
# they already have, and it reads them from HERE rather than keeping
# its own copy. Keep the markers if you move the lines.
# >>> gskit wiring
EE_CFLAGS  += -std=c99 -Wall -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
EE_LIBS     = -lgskit -ldmakit
EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib
# <<< gskit wiring

# No -Werror, deliberately: this file is yours the moment it is
# written, and a starter that refuses to build over a warning in code
# it did not write is a starter nobody keeps.

ifdef NOPAD
EE_CFLAGS += -DPS2UI_STARTER_NOPAD
endif

ifdef SCREEN
EE_CFLAGS += -DPS2UI_STARTER_SCREEN='"$(SCREEN)"'
endif

# `make ARENA=4096` if the bake asks for more than the 16 KiB default.
# The number is on `ps2ui build`'s `arena N bytes` line.
ifdef ARENA
EE_CFLAGS += -DPS2UI_STARTER_ARENA=$(ARENA)
endif

all: $(EE_BIN)

# bin2c turns the blob into a C array named after the output file, so
# ui_uib.c defines `ui_uib` and `size_ui_uib` -- the two symbols main.c
# declares extern.
ui_uib.c: $(UIB)
	$(PS2SDK)/bin/bin2c $(UIB) ui_uib.c ui_uib

# ps2ui.o has no rule of its own on purpose: PS2SDK's implicit %.o rule
# already compiles ps2ui.c with the full ee/include set, and a custom
# rule here would miss tamtypes.h and friends.

clean:
	rm -f $(EE_BIN) $(EE_OBJS) ui_uib.c

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
