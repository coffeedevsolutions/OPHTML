/* Host shim for ps2sdk's fileio.h.
 *
 * The streaming bench reads mass:/ps2ui/cover*.raw through fioOpen /
 * fioRead / fioClose. Those live in ps2sdk and do not exist here, so
 * without this the COVERS build could only ever be compiled inside the
 * ps2dev container -- which is exactly the push-and-hope that made
 * `make syntax-check` necessary in the first place: the telemetry
 * build once shipped an `asm volatile` that -std=c99 rejects, with
 * every local suite green.
 *
 * Declarations only, and deliberately never linked. `syntax-check`
 * runs -fsyntax-only, so a body here would be dead weight that could
 * drift from the real driver's behaviour and teach someone the wrong
 * thing. The console build never sees this file: the ps2dev include
 * path finds the real one first. */
#ifndef PS2UI_HOST_SHIM_FILEIO_H
#define PS2UI_HOST_SHIM_FILEIO_H

/* Same values ps2sdk uses. Only O_RDONLY is exercised here. */
#define O_RDONLY 0x0001

int fioOpen(const char *name, int mode);
int fioRead(int fd, void *ptr, int size);
int fioClose(int fd);

#endif /* PS2UI_HOST_SHIM_FILEIO_H */
