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

# The reusable launcher core, archived into a static library a
# downstream launcher links against. No UI and no main of its own; see
# ophtml_console.h and README.md's "Building a launcher on the core".
CORE_LIB  = libophtml-console.a
CORE_OBJS = library.o scan.o storage.o launch.o resolver.o state.o

# The built-in theme. examples/console/build.sh bakes it; a theme.uib
# on a drive overrides it at run time, so this only decides what shows
# when there is none.
THEME ?= ../examples/console/build/ui.uib

# What this ELF links on top of the core: its own main, the baked
# theme, the ps2ui runtime it draws through, and the generated IOP
# module table storage.c links against. main.c is the core's first
# consumer, nothing more -- a downstream launcher brings its own.
EE_OBJS = main.o theme_uib.o ps2ui.o irx_table.o

# In load order. storage.c keeps the same list with what each one's
# failure means; a name here that storage.c does not list is carried
# and never loaded, and the reverse is a module storage.c cannot find.
IRX = iomanX fileXio sio2man mcman mcserv freepad mmceman ps2dev9 \
      bdm bdmfs_fatfs ata_bd usbd_mini usbmass_bd_mini mx4sio_bd_mini

EE_CFLAGS  += -std=c99 -Wall -I$(PS2DEV)/gsKit/include -I$(PS2SDK)/ports/include
EE_LDFLAGS += -L$(PS2DEV)/gsKit/lib -L$(PS2SDK)/ports/lib
# -L. -lophtml-console first: the core archive, before the system libs
# its members call into (-lpatches for the loader, -lfileXio for the
# reads). -lelf-loader, not -nocolour: the loader's background colours
# are the only record of a launch that fails after the console lets go.
EE_LIBS     = -L. -lophtml-console -lgskit -ldmakit -lpad -lpatches \
              -lfileXio -lelf-loader

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

# The IOP module list, for a consumer that generates its own table from
# this one rather than a copy (examples/console-min does). `make -s -C
# console print-irx` prints it on one line.
print-irx:
	@echo $(IRX)

# Archive the core objects. The ELF links it through -lophtml-console
# (EE_LIBS), so the link needs it built first. $(EE_AR) is Makefile.pref's
# ar for the EE toolchain.
$(CORE_LIB): $(CORE_OBJS)
	$(EE_AR) rcs $@ $(CORE_OBJS)

$(EE_BIN): $(CORE_LIB)

ps2ui.c: ../runtime/ps2ui.c ../runtime/ps2ui.h
	cp ../runtime/ps2ui.h ps2ui.h
	cp ../runtime/ps2ui.c ps2ui.c

ps2ui.o: ps2ui.c
main.o: ps2ui.c irx_table.h mock_library.h
# storage.c is a core object, but it includes the generated table, so
# the archive still waits on embed_irx.sh.
storage.o: irx_table.h

theme_uib.c: $(THEME)
	$(PS2SDK)/bin/bin2c $(THEME) theme_uib.c theme_uib

irx_table.c irx_table.h: embed_irx.sh
	sh embed_irx.sh . $(IRX)

clean: objclean
	rm -f $(EE_BIN)

# Everything but the ELF, so the plain and MOCK builds can be made one
# after the other from one checkout without the second deleting the
# first -- the sample's objclean, for the sample's reason. The core
# objects and the archive go too, so a ROMPAD rebuild re-archives a
# storage.o built with the flag.
objclean:
	rm -f $(EE_OBJS) $(CORE_OBJS) $(CORE_LIB) \
	      theme_uib.c ps2ui.c ps2ui.h irx_table.c irx_table.h

include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
