/* Storage bring-up: the IOP modules the console carries, and the
 * devices they mount. PS2-only; see library.h for the portable half. */

#ifndef CONSOLE_STORAGE_H
#define CONSOLE_STORAGE_H

#include "library.h"

/* massN: is BDM's numbering (one per partition it mounts), mmce0: and
 * mmce1: are the two memory card slots. Twelve covers a USB stick, an
 * HDD with a couple of exFAT partitions and both slots with room over. */
#define CONSOLE_DEVICES_MAX 12

typedef struct {
    char        mount[8];  /* "mass0:", "mmce1:" -- no trailing slash */
    console_bsd bsd;
} console_device;

/* Which of the optional modules came up, for the status line. A console
 * with no HDD refuses ata_bd, a slim without an MMCE has nothing for
 * mmceman to find, and neither is an error: the drive is just not there.
 * The mandatory set (iomanX, fileXio, sio2man, the pad driver, bdm and
 * the exFAT/FAT filesystem) is not reported here, because without it
 * console_storage_start fails. */
enum {
    CONSOLE_HAVE_USB    = 1 << 0,
    CONSOLE_HAVE_ATA    = 1 << 1,
    CONSOLE_HAVE_MX4SIO = 1 << 2,
    CONSOLE_HAVE_MMCE   = 1 << 3
};

/* Reset the IOP and load the console's modules from the ELF.
 *
 * MX4SIO AND MMCE ARE EXCLUSIVE. Both drive the memory card port's
 * SIO2 bus; with both loaded, mmceman claims the slot the MX4SIO
 * adapter sits in (NHDDL documents the same conflict and makes MX4SIO
 * opt-in for it). So `mx4sio` chooses: nonzero loads mx4sio_bd and
 * leaves mmceman out, zero does the opposite.
 *
 * Returns a CONSOLE_HAVE_* mask, or -1 if a mandatory module failed --
 * `failed` then names it, for the screen. */
int console_storage_start(int mx4sio, const char **failed);

/* The devices mounted right now, in mount order. A USB stick takes a
 * second or two to appear after usbmass_bd loads, so the caller polls
 * this while drawing rather than calling it once. */
int console_storage_devices(console_device *out, int max);

#endif /* CONSOLE_STORAGE_H */
