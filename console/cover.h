/* Cover art: decoding OPL's ART/<ID>_COV.png to RGBA8888 for a theme's
 * streamed cover slot (game-{i}-cover / sel-cover). See BACKLOG.md F58.
 *
 * WHY THIS IS ITS OWN FILE, AND HOST-ONLY FOR NOW. F58 splits three
 * ways: decode a cover, wire it into a texture slot, and cache/evict
 * covers against a 4 MB VRAM and a 1500-game list. This file is the
 * first part -- decode -- which is pure (PNG bytes in, pixels out) and
 * host-testable, so tests/test_library.c runs it on the host against
 * the same code the console will compile. The EE wiring (resizing a
 * cover to a slot's reservation and handing it to ps2ui_tex_set) and
 * the cache are the next slices; THIS file is deliberately not yet in
 * the core archive (CORE_OBJS) or the EE build, because it depends on
 * zlib for inflate and the EE side of that dependency belongs with the
 * wiring slice, not here.
 *
 * WHY zlib AND NOT A HAND-ROLLED INFLATE. A cover is an untrusted file
 * off somebody's drive, exactly the input class S2 fuzzes the .uib
 * loader over. A hand-written DEFLATE decoder is the kind of parser
 * that class of input breaks; zlib is the vetted one. This file owns
 * the PNG container and the unfilter step -- which it validates and
 * which the host suite hammers with malformed input -- and hands the
 * compressed image data to zlib.
 *
 * UNLIKE library.c THIS ALLOCATES. An image's size is not known until
 * its header is read, so the decoder mallocs the pixel buffer and the
 * caller frees it with console_image_free. It still touches no file:
 * reading the bytes off a drive is the caller's POSIX I/O, the same
 * split as scan.c (the reader) and library.c (the parser). */

#ifndef CONSOLE_COVER_H
#define CONSOLE_COVER_H

#include <stddef.h>
#include <stdint.h>

/* A cover is at most this many pixels on a side. OPL covers are small
 * (around 140x200); the cap is generous for one and, more to the point,
 * bounds what a malformed or hostile IHDR can make the decoder allocate
 * before a single pixel is read -- the decompression-bomb guard S3 put
 * on the bakers, here on the console's own decode. */
#define CONSOLE_COVER_MAX_DIM 1024

/* A decoded cover: RGBA8888, row-major, no row padding, `w * h * 4`
 * bytes in `rgba`. Freed with console_image_free. */
typedef struct {
    uint32_t  w, h;
    uint8_t  *rgba;
} console_image;

/* Decode a PNG to RGBA8888. Supports the 8-bit colour types a cover is
 * ever stored as -- grayscale, grayscale+alpha, truecolour,
 * truecolour+alpha -- and indexed colour at bit depth 1/2/4/8 with an
 * optional tRNS palette-alpha chunk. Non-interlaced only.
 *
 * Returns 0 on success, with out->rgba malloc'd (w*h*4 bytes) and
 * out->w/out->h set. Returns a negative CONSOLE_PNG_ERR_* on any
 * truncated, corrupt, oversized or unsupported input, having allocated
 * nothing the caller must free. 16-bit, interlaced, and colour-key
 * (non-indexed) tRNS are refused rather than mis-decoded. */
int console_png_decode(const void *bytes, size_t len, console_image *out);

/* Free an image's pixels and zero it. Safe on a zeroed/failed image. */
void console_image_free(console_image *img);

#define CONSOLE_PNG_OK            0
#define CONSOLE_PNG_ERR_SIG      -1  /* not a PNG (bad 8-byte signature) */
#define CONSOLE_PNG_ERR_TRUNC    -2  /* a read ran past the end          */
#define CONSOLE_PNG_ERR_CHUNK    -3  /* bad chunk length, CRC or order   */
#define CONSOLE_PNG_ERR_IHDR     -4  /* bad/unsupported IHDR fields      */
#define CONSOLE_PNG_ERR_COLOR    -5  /* unsupported colour-type/depth    */
#define CONSOLE_PNG_ERR_PLTE     -6  /* indexed with a missing/bad PLTE  */
#define CONSOLE_PNG_ERR_INFLATE  -7  /* zlib rejected the image data     */
#define CONSOLE_PNG_ERR_FILTER   -8  /* unknown per-scanline filter byte */
#define CONSOLE_PNG_ERR_SIZE     -9  /* dimensions exceed the cover cap  */
#define CONSOLE_PNG_ERR_MEM     -10  /* out of memory                    */

#endif /* CONSOLE_COVER_H */
