/* See launch.h.
 *
 * THE HANDOFF DOES NOT RESET THE IOP, and that is the whole design.
 * PS2SDK's elf-loader copies a small loader into the kernel's unused
 * memory, jumps to it, and the loader reads the target ELF off
 * whatever device the IOP can currently see. Its default entry point,
 * LoadELFFromFile, then resets the IOP before starting the ELF -- which
 * would throw away the USB, HDD and SD drivers the console loaded, and
 * with them the device Neutrino's -qb quick boot is about to read the
 * game from. The NoReset entry point (ps2sdk 8890d8b, June 2026) skips
 * that, so Neutrino starts on the IOP the console built.
 *
 * THE PROTOTYPE IS DECLARED HERE, NOT INCLUDED. The ps2dev image
 * installs two libraries that both ship an elf-loader.h -- elf-loader
 * and elf-loader2 -- and the second one's header is the one left in
 * ee/include. It lacks the NoReset declaration while libelf-loader.a
 * exports the symbol (nm, ghcr.io/ps2dev/ps2dev:latest built
 * 2026-09-22). Declaring it ourselves compiles against either header
 * and links against the library that has it; if an image ever drops
 * the symbol, the elf job fails at the link with its name.
 *
 * THE LOADER PAINTS ITS PROGRESS. libelf-loader (not -nocolour) sets
 * the GS background colour at each step, so a launch that dies leaves
 * a solid colour naming where: magenta, the ELF would not load; red,
 * bad arguments. README.md lists them for the bench. */

#include "launch.h"

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern int LoadELFFromFileWithPartitionNoReset(const char *filename,
                                               const char *partition,
                                               int argc, char *argv[]);

static int exists(const char *path)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    close(fd);
    return 1;
}

static int try_path(char *out, size_t cap, const char *a, const char *b)
{
    if ((size_t)snprintf(out, cap, "%s%s", a, b) >= cap) return 0;
    return exists(out);
}

int console_find_neutrino(const char *launch_dir,
                          const console_device *devs, int n_devs,
                          char *out, size_t cap)
{
    static const char *const cards[] = {
        "mc0:/APPS/neutrino/neutrino.elf",
        "mc1:/APPS/neutrino/neutrino.elf",
    };
    unsigned i;
    int d;

    if (launch_dir && launch_dir[0]) {
        if (try_path(out, cap, launch_dir, "neutrino/neutrino.elf")) return 1;
        if (try_path(out, cap, launch_dir, "neutrino.elf")) return 1;
    }
    for (d = 0; d < n_devs; d++)
        if (try_path(out, cap, devs[d].mount, "/neutrino/neutrino.elf"))
            return 1;
    for (i = 0; i < sizeof cards / sizeof cards[0]; i++)
        if (try_path(out, cap, cards[i], "")) return 1;
    return 0;
}

int console_launch(const char *neutrino, const console_game *game)
{
    static char store[CONSOLE_PATH_MAX + 64];
    char *argv[4];
    int argc = console_neutrino_args(game, store, sizeof store, argv, 4);

    if (argc < 0) return -1;
    /* Neutrino finds its modules and config relative to its own
     * directory, which it takes from argv[0]. The loader supplies
     * argv[0] as partition + filename; with no partition that is the
     * path as given, so it must be the full one we found. */
    LoadELFFromFileWithPartitionNoReset(neutrino, NULL, argc, argv);
    return -2;
}
