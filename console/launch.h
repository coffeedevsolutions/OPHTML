/* Handing a game to Neutrino. PS2-only. */

#ifndef CONSOLE_LAUNCH_H
#define CONSOLE_LAUNCH_H

#include "library.h"
#include "storage.h"

/* Find neutrino.elf. Looks, in order:
 *
 *   <launch dir>/neutrino/neutrino.elf   beside the console
 *   <launch dir>/neutrino.elf
 *   <each device>/neutrino/neutrino.elf  the release zip, unpacked at a root
 *   mc0: and mc1: /APPS/neutrino/neutrino.elf
 *
 * which is NHDDL's search, less the paths for devices the console does
 * not mount. Writes the first that opens into `out` and returns 1;
 * returns 0 if none does. */
int console_find_neutrino(const char *launch_dir,
                          const console_device *devs, int n_devs,
                          char *out, size_t cap);

/* Start `game` under the Neutrino at `neutrino`. Does not return on
 * success. Returns a negative number if the command line could not be
 * built or the loader refused the file.
 *
 * THE CALLER MUST STOP THE PAD FIRST (padPortClose + padEnd). The pad
 * driver on the IOP keeps DMAing controller state into the EE buffer
 * it was given, every frame, and the loader is about to wipe EE memory
 * and put Neutrino there. A pad left running writes into Neutrino. */
int console_launch(const char *neutrino, const console_game *game);

#endif /* CONSOLE_LAUNCH_H */
