/* See storage.h.
 *
 * THE MODULE LIST AND ITS ORDER ARE NHDDL'S, and that is deliberate.
 * NHDDL (github.com/pcm720/nhddl) is a Neutrino frontend that loads
 * this exact set from the ELF, in this order, on hardware people use
 * every day, and it launches Neutrino with -qb afterwards -- which
 * reads the game through whatever these modules mounted (see the -qb
 * note in library.c). Starting from a set that is known to boot a game
 * means the first bench sitting tests the console, not a guess at
 * which drivers coexist. What is NOT carried over: iLink, UDPFS and
 * the APA/HDL stack, which the console does not scan yet.
 *
 * WHY THE ELF CARRIES THEM AT ALL is the lesson of F-030: whatever
 * launched us (wLaunchELF, FMCB, OPL's app list) went through
 * LoadExecPS2, which resets the IOP, so no driver it had loaded is
 * still there. */

#include "storage.h"

#include <kernel.h>
#include <iopcontrol.h>
#include <loadfile.h>
#include <sbv_patches.h>
#include <sifrpc.h>
#include <stdio.h>
#include <string.h>

#define NEWLIB_PORT_AWARE
#include <fileXio_rpc.h>
#include <usbhdfsd-common.h>

#include "irx_table.h"

/* What a module is for decides what its failure means. */
enum {
    NEED,   /* nothing works without it: fail the bring-up */
    SIO,    /* the SDK's SIO2 stack: NEED, unless ROMPAD swaps it out */
    USB,    /* each of these only takes its device away */
    ATA,
    MX4SIO,
    MMCE
};

static const struct {
    const char *name;
    int role;
} modules[] = {
    { "iomanX",          NEED },
    { "fileXio",         NEED },
    /* The SDK's sio2man and pad driver rather than rom0:SIO2MAN and
     * rom0:PADMAN, which is what the starter loads. The ROM pair
     * cannot share the bus with mx4sio_bd or mmceman, which need the
     * SDK's sio2man; loading one sio2man and building both the pad and
     * the card-slot devices on it is the only arrangement that works
     * for all three. */
    { "sio2man",         SIO },
    { "mcman",           SIO },
    { "mcserv",          SIO },
    { "freepad",         SIO },
    { "mmceman",         MMCE },
    /* DEV9 powers the expansion bay the HDD sits in. It is refused on
     * a console with nothing there, which only costs the HDD. */
    { "ps2dev9",         ATA },
    { "bdm",             NEED },
    /* FatFs with exFAT enabled: one filesystem for FAT32 USB sticks,
     * exFAT HDDs and microSD cards alike. */
    { "bdmfs_fatfs",     NEED },
    { "ata_bd",          ATA },
    { "usbd_mini",       USB },
    { "usbmass_bd_mini", USB },
    { "mx4sio_bd_mini",  MX4SIO },
};

static const irx_module *irx_find(const char *name)
{
    int i;
    for (i = 0; i < n_irx_modules; i++)
        if (strcmp(irx_modules[i].name, name) == 0) return &irx_modules[i];
    return NULL;
}

/* Load one embedded module. A negative id is a load failure; a
 * non-negative id with mod_res 1 (NO_RESIDENT_END) is a module that
 * ran, looked for its hardware, did not find it and unloaded itself --
 * which is how ata_bd says "no HDD". Both count as not loaded. */
static int load(const irx_module *m)
{
    int res = 0;
    int id = SifExecModuleBuffer((void *)m->data, *m->size, 0, NULL, &res);
    return (id >= 0 && res != 1) ? 0 : -1;
}

int console_storage_start(int mx4sio, const char **failed)
{
    unsigned i;
    int have = CONSOLE_HAVE_USB | CONSOLE_HAVE_ATA |
               (mx4sio ? CONSOLE_HAVE_MX4SIO : CONSOLE_HAVE_MMCE);

    SifInitRpc(0);
    while (!SifIopReset("", 0)) {}
    while (!SifIopSync()) {}
    SifInitRpc(0);
    SifLoadFileInit();
    /* Module loading from EE memory, and loading an ELF from a path
     * that is not rom0: -- the second is what LoadELFFromFile needs to
     * start Neutrino off a mass: or mmce: path at launch time. */
    sbv_patch_enable_lmb();
    sbv_patch_disable_prefix_check();
    sbv_patch_fileio();

#ifdef CONSOLE_ROMPAD
    /* `make ROMPAD=1`: the ROM's SIO2MAN and PADMAN instead of the
     * SDK's sio2man and freepad, and so no memory card, MMCE or MX4SIO
     * driver, since those need the SDK's sio2man. This build exists for
     * one reason: Play! answers pad reads from its own stand-in for the
     * ROM pair, and the SDK drivers get no input under it (measured
     * 2026-09-24: IOP reset + rom0 pair, focus moves; IOP reset + SDK
     * sio2man + freepad or padman, nothing). So the emulator can drive
     * the console's list with a pad only through the ROM pair. The
     * shipped ELF never takes this path: freepad is what NHDDL runs on
     * consoles, and the one thing this build cannot vouch for. */
    if (SifLoadModule("rom0:SIO2MAN", 0, NULL) < 0 ||
        SifLoadModule("rom0:PADMAN", 0, NULL) < 0) {
        if (failed) *failed = "rom0:PADMAN";
        return -1;
    }
    have &= ~(CONSOLE_HAVE_MMCE | CONSOLE_HAVE_MX4SIO);
#endif

    for (i = 0; i < sizeof modules / sizeof modules[0]; i++) {
        const irx_module *m;
        int role = modules[i].role;

#ifdef CONSOLE_ROMPAD
        if (role == SIO || role == MMCE || role == MX4SIO) continue;
#endif
        if (role == MMCE && mx4sio) continue;
        if (role == MX4SIO && !mx4sio) continue;
        /* ata_bd without ps2dev9 cannot find the bay; do not ask. */
        if (role == ATA && !(have & CONSOLE_HAVE_ATA)) continue;

        m = irx_find(modules[i].name);
        if (m == NULL || load(m) != 0) {
            if (role == NEED || role == SIO) {
                if (failed) *failed = modules[i].name;
                return -1;
            }
            if (role == USB)    have &= ~CONSOLE_HAVE_USB;
            if (role == ATA)    have &= ~CONSOLE_HAVE_ATA;
            if (role == MX4SIO) have &= ~CONSOLE_HAVE_MX4SIO;
            if (role == MMCE)   have &= ~CONSOLE_HAVE_MMCE;
        }
    }

    if (fileXioInit() < 0) {
        if (failed) *failed = "fileXioInit";
        return -1;
    }
    return have;
}

int console_storage_devices(console_device *out, int max)
{
    int n = 0, i;
    char mount[8];

    /* BDM numbers what it mounts from mass0: upward with no gaps, so
     * the first one that does not open is the end. */
    for (i = 0; i < 10 && n < max; i++) {
        char driver[16] = {0};
        int fd;

        snprintf(mount, sizeof mount, "mass%d:", i);
        fd = fileXioDopen(mount);
        if (fd < 0) break;
        if (fileXioIoctl2(fd, USBMASS_IOCTL_GET_DRIVERNAME, NULL, 0,
                          driver, sizeof driver - 1) >= 0) {
            console_bsd bsd = console_bsd_from_driver(driver);
            if (bsd != CONSOLE_BSD_NONE) {
                strcpy(out[n].mount, mount);
                out[n].bsd = bsd;
                n++;
            }
        }
        fileXioDclose(fd);
    }

    /* MMCE is not BDM: mmceman is a filesystem of its own, one device
     * per memory card slot. */
    for (i = 0; i < 2 && n < max; i++) {
        int fd;
        snprintf(mount, sizeof mount, "mmce%d:", i);
        fd = fileXioDopen(mount);
        if (fd < 0) continue;
        fileXioDclose(fd);
        strcpy(out[n].mount, mount);
        out[n].bsd = CONSOLE_BSD_MMCE;
        n++;
    }
    return n;
}
