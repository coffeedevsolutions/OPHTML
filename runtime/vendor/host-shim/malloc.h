/* <malloc.h> for hosts that do not have one.
 *
 * `vendor/gsKit/src/gsTexture.c` is verbatim upstream and includes
 * <malloc.h> at file scope. That header is a glibc-ism: Linux has it,
 * and macOS does not -- there the same declarations live in
 * <stdlib.h>, which is where the C standard puts them. So
 * `make -C runtime test` compiled on Linux and died at the include on
 * a Mac, and CI never saw it because every job that builds the runtime
 * runs on ubuntu.
 *
 * WHY THIS IS A SHIM AND NOT THE fileio.h MISTAKE, because the README
 * beside this directory forbids that one and the distinction is the
 * whole justification. That rule is about PS2SDK APIs: a shim
 * describing `fioOpen` made the host green over a call ps2sdk's newlib
 * port rejects outright, so the shim asserted conformance it could not
 * know. Nothing of the kind is happening here. <malloc.h> is not a
 * PS2SDK header, this file claims nothing about the EE, and the
 * console build never sees this directory at all -- PS2SDK ships its
 * own <malloc.h> and only the host Makefiles put vendor/ on the
 * include path. This is a portability alias between two spellings of
 * the same standard declarations, on the host, for one vendored file.
 *
 * It is also exactly what host-shim/kernel.h already does for the same
 * file: gsTexture.c includes <kernel.h> too, and that one has stood
 * here since the vendoring landed.
 *
 * AND IT COSTS NOTHING TO BE SURE: the host build compiles this file
 * with only -DF_gsKit_texture_size, which yields gsKit_texture_size
 * alone, and that function names no allocator. Measured, not assumed
 * -- zero hits for malloc/calloc/realloc/free/memalign inside the
 * guarded block. The include has to RESOLVE; nothing needs it to
 * declare anything.
 */
#ifndef PS2UI_HOST_SHIM_MALLOC_H
#define PS2UI_HOST_SHIM_MALLOC_H

#include <stdlib.h>

#endif
