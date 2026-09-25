# The OPHTML console ELF. Needs the ps2dev toolchain:
#
#   docker run --rm -v "$PWD:/work" -w /work ghcr.io/ps2dev/ps2dev \
#       sh -c 'apk add --no-cache make && make -C console'
#
#   make                          # the built-in theme is examples/console
#   make THEME=path/to/ui.uib     # build a different theme in instead
#   make clean
#
# The portable half has a host test: `make -C console/tests test`.

EE_BIN = ophtml.elf

# The built-in theme. examples/console/build.sh bakes it; a theme.uib
# on a drive overrides it at run time, so this only decides what shows
# when there is none.
THEME ?= ../examples/console/build/ui.uib

EE_OBJS = main.o library.o scan.o storage.o launch.o ps2ui.o \
          theme_uib.o irx_table.o

# In load order. storage.c keeps the same list with what each one's
# failure means; a name here that storage.c does not list is carried
# and never loaded, and the reverse is a module storage.c cannot find.
IRX = iomanX fileXio sio2man mcman mcserv freepad mmceman ps2dev9 \
      bdm bdmfs_fatfs ata_bd usbd_mini usbmass_bd_mini mx4sio_bd_mini

EE_CFLAGS  += -std=c99 -Wall -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib
# -lelf-loader, not -nocolour: the loader's background colours are the
# only record of a launch that fails after the console has let go.
EE_LIBS     = -lgskit -ldmakit -lpad -lpatches -lfileXio -lelf-loader

# `make MOCK=1 EE_BIN=ophtml-mock.elf` lists mock_library.h's games
# as if a drive held them. For the emulator, which has no drive to
# offer: hw.yml boots it and diffs the frame against the previewer
# drawing the same list. It also scans for real, so it is harmless on
# a console -- but a launch of a mock game has nothing to start.
ifdef MOCK
EE_CFLAGS += -DCONSOLE_MOCK
endif

# `make MOCK=1 ROMPAD=1 EE_BIN=ophtml-nav.elf`: the MOCK build on the
# ROM's pad driver, so the emulator can press buttons at it. Emulator
# only -- storage.c says why, and what it gives up.
ifdef ROMPAD
EE_CFLAGS += -DCONSOLE_ROMPAD
endif

all: $(EE_BIN)

ps2ui.c: ../runtime/ps2ui.c ../runtime/ps2ui.h
	cp ../runtime/ps2ui.h ps2ui.h
	cp ../runtime/ps2ui.c ps2ui.c

ps2ui.o: ps2ui.c
main.o: ps2ui.c irx_table.h mock_library.h
storage.o: irx_table.h

theme_uib.c: $(THEME)
	$(PS2SDK)/bin/bin2c $(THEME) theme_uib.c theme_uib

irx_table.c irx_table.h: embed_irx.sh
	sh embed_irx.sh . $(IRX)

clean: objclean
	rm -f $(EE_BIN)

# Everything but the ELF, so the plain and MOCK builds can be made one
# after the other from one checkout without the second deleting the
# first -- the sample's objclean, for the sample's reason.
objclean:
	rm -f $(EE_OBJS) theme_uib.c ps2ui.c ps2ui.h irx_table.c irx_table.h

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
