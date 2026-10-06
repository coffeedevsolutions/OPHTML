/* See cover.h. */

#include "cover.h"

#include <stdlib.h>
#include <string.h>

#include <zlib.h>

/* Big-endian 32-bit read from a bounds-checked cursor. */
static uint32_t be32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | (uint32_t)p[3];
}

/* The Paeth predictor (PNG spec 9.4), on three byte neighbours. */
static int paeth(int a, int b, int c)
{
    int p = a + b - c;
    int pa = p > a ? p - a : a - p;
    int pb = p > b ? p - b : b - p;
    int pc = p > c ? p - c : c - p;
    if (pa <= pb && pa <= pc) return a;
    return pb <= pc ? b : c;
}

/* Reverse one scanline's filter, in place, given the already-unfiltered
 * previous line (`prev`, NULL for the first). `bpp` is the byte step to
 * the pixel to the left; `stride` is the line length in bytes. */
static int unfilter(uint8_t filter, uint8_t *cur, const uint8_t *prev,
                    size_t stride, size_t bpp)
{
    size_t i;
    switch (filter) {
    case 0: /* None */
        break;
    case 1: /* Sub */
        for (i = bpp; i < stride; i++) cur[i] = (uint8_t)(cur[i] + cur[i - bpp]);
        break;
    case 2: /* Up */
        if (prev) for (i = 0; i < stride; i++) cur[i] = (uint8_t)(cur[i] + prev[i]);
        break;
    case 3: /* Average */
        for (i = 0; i < stride; i++) {
            int a = i >= bpp ? cur[i - bpp] : 0;
            int b = prev ? prev[i] : 0;
            cur[i] = (uint8_t)(cur[i] + (a + b) / 2);
        }
        break;
    case 4: /* Paeth */
        for (i = 0; i < stride; i++) {
            int a = i >= bpp ? cur[i - bpp] : 0;
            int b = prev ? prev[i] : 0;
            int c = (prev && i >= bpp) ? prev[i - bpp] : 0;
            cur[i] = (uint8_t)(cur[i] + paeth(a, b, c));
        }
        break;
    default:
        return CONSOLE_PNG_ERR_FILTER;
    }
    return 0;
}

static const uint8_t PNG_SIG[8] = { 137, 80, 78, 71, 13, 10, 26, 10 };

int console_png_decode(const void *bytes, size_t len, console_image *out)
{
    const uint8_t *p = (const uint8_t *)bytes;
    size_t pos;
    uint32_t w = 0, h = 0;
    int depth = 0, color = -1, channels = 0;
    int seen_ihdr = 0, seen_idat = 0, seen_end = 0;
    size_t bpp = 0, stride = 0, raw_len = 0;

    uint8_t  palette[256][3];
    int      pal_n = 0;
    uint8_t  pal_a[256];               /* tRNS; default opaque */

    uint8_t *idat = NULL;              /* concatenated IDAT payloads */
    size_t   idat_len = 0, idat_cap = 0;
    uint8_t *raw = NULL;               /* inflated, filtered scanlines */
    uint8_t *rgba = NULL;
    int rc = CONSOLE_PNG_ERR_CHUNK;

    memset(out, 0, sizeof *out);
    memset(pal_a, 0xFF, sizeof pal_a);

    if (len < 8 || memcmp(p, PNG_SIG, 8) != 0) return CONSOLE_PNG_ERR_SIG;
    pos = 8;

    /* Walk chunks: [len:4][type:4][data:len][crc:4]. */
    while (pos + 8 <= len) {
        uint32_t clen = be32(p + pos);
        const uint8_t *type = p + pos + 4;
        const uint8_t *data = p + pos + 8;

        /* clen is attacker-controlled: guard the add before using it. */
        if (clen > len || pos + 12 + clen > len) { rc = CONSOLE_PNG_ERR_TRUNC; goto done; }
        if (crc32(crc32(0, type, 4), data, clen) != be32(data + clen)) {
            rc = CONSOLE_PNG_ERR_CHUNK; goto done;
        }

        if (memcmp(type, "IHDR", 4) == 0) {
            if (seen_ihdr || clen != 13) { rc = CONSOLE_PNG_ERR_IHDR; goto done; }
            w = be32(data); h = be32(data + 4);
            depth = data[8]; color = data[9];
            if (data[10] != 0 || data[11] != 0) { rc = CONSOLE_PNG_ERR_IHDR; goto done; }
            if (data[12] != 0) { rc = CONSOLE_PNG_ERR_IHDR; goto done; } /* interlaced */
            if (w == 0 || h == 0) { rc = CONSOLE_PNG_ERR_IHDR; goto done; }
            if (w > CONSOLE_COVER_MAX_DIM || h > CONSOLE_COVER_MAX_DIM) {
                rc = CONSOLE_PNG_ERR_SIZE; goto done;
            }
            switch (color) {
            case 0: channels = 1; if (depth != 8) { rc = CONSOLE_PNG_ERR_COLOR; goto done; } break;
            case 2: channels = 3; if (depth != 8) { rc = CONSOLE_PNG_ERR_COLOR; goto done; } break;
            case 4: channels = 2; if (depth != 8) { rc = CONSOLE_PNG_ERR_COLOR; goto done; } break;
            case 6: channels = 4; if (depth != 8) { rc = CONSOLE_PNG_ERR_COLOR; goto done; } break;
            case 3: channels = 1;
                if (depth != 1 && depth != 2 && depth != 4 && depth != 8) {
                    rc = CONSOLE_PNG_ERR_COLOR; goto done;
                }
                break;
            default: rc = CONSOLE_PNG_ERR_COLOR; goto done;
            }
            /* stride = ceil(w * channels * depth / 8); bpp = ceil(bits/8),
             * at least 1, which is the filter's left-neighbour step. */
            stride = ((size_t)w * channels * depth + 7) / 8;
            bpp = ((size_t)channels * depth + 7) / 8;
            if (bpp == 0) bpp = 1;
            raw_len = (stride + 1) * (size_t)h;   /* +1 filter byte per row */
            seen_ihdr = 1;
        } else if (memcmp(type, "PLTE", 4) == 0) {
            if (!seen_ihdr || seen_idat || clen == 0 || clen % 3 != 0 || clen > 256 * 3) {
                rc = CONSOLE_PNG_ERR_PLTE; goto done;
            }
            pal_n = (int)(clen / 3);
            memcpy(palette, data, clen);
        } else if (memcmp(type, "tRNS", 4) == 0) {
            /* Only indexed transparency is handled; a colour-key tRNS on
             * a truecolour/grey image is refused rather than ignored, so
             * a transparent cover never silently decodes opaque. */
            if (!seen_ihdr) { rc = CONSOLE_PNG_ERR_CHUNK; goto done; }
            if (color != 3) { rc = CONSOLE_PNG_ERR_COLOR; goto done; }
            if (clen > 256) { rc = CONSOLE_PNG_ERR_PLTE; goto done; }
            memcpy(pal_a, data, clen);
        } else if (memcmp(type, "IDAT", 4) == 0) {
            if (!seen_ihdr) { rc = CONSOLE_PNG_ERR_CHUNK; goto done; }
            if (color == 3 && pal_n == 0) { rc = CONSOLE_PNG_ERR_PLTE; goto done; }
            if (clen) {
                if (idat_len + clen > idat_cap) {
                    size_t ncap = idat_cap ? idat_cap * 2 : clen + 64;
                    uint8_t *n;
                    while (ncap < idat_len + clen) ncap *= 2;
                    n = (uint8_t *)realloc(idat, ncap);
                    if (!n) { rc = CONSOLE_PNG_ERR_MEM; goto done; }
                    idat = n; idat_cap = ncap;
                }
                memcpy(idat + idat_len, data, clen);
                idat_len += clen;
            }
            seen_idat = 1;
        } else if (memcmp(type, "IEND", 4) == 0) {
            seen_end = 1;
            pos += 12 + clen;
            break;
        }
        /* Unknown chunks (ancillary) are skipped; CRC already checked. */
        pos += 12 + clen;
    }

    if (!seen_ihdr || !seen_idat || !seen_end) { rc = CONSOLE_PNG_ERR_CHUNK; goto done; }

    /* Inflate into exactly the filtered-scanline size IHDR implies. */
    raw = (uint8_t *)malloc(raw_len ? raw_len : 1);
    if (!raw) { rc = CONSOLE_PNG_ERR_MEM; goto done; }
    {
        uLongf dst = (uLongf)raw_len;
        int zr = uncompress(raw, &dst, idat, (uLong)idat_len);
        if (zr != Z_OK || dst != raw_len) { rc = CONSOLE_PNG_ERR_INFLATE; goto done; }
    }

    /* Unfilter each scanline in place, dropping its leading filter byte. */
    {
        uint8_t *prev = NULL, *cur;
        uint32_t y;
        for (y = 0; y < h; y++) {
            uint8_t *line = raw + (size_t)y * (stride + 1);
            uint8_t filter = line[0];
            cur = line + 1;
            rc = unfilter(filter, cur, prev, stride, bpp);
            if (rc) goto done;
            /* Shift the unfiltered bytes down over the filter byte so the
             * rows become contiguous `stride` blocks for the expand below. */
            memmove(raw + (size_t)y * stride, cur, stride);
            prev = raw + (size_t)y * stride;
        }
    }

    /* Expand to RGBA8888. */
    rgba = (uint8_t *)malloc((size_t)w * h * 4);
    if (!rgba) { rc = CONSOLE_PNG_ERR_MEM; goto done; }
    {
        uint32_t x, y;
        for (y = 0; y < h; y++) {
            const uint8_t *row = raw + (size_t)y * stride;
            uint8_t *o = rgba + (size_t)y * w * 4;
            for (x = 0; x < w; x++, o += 4) {
                switch (color) {
                case 0: { uint8_t g = row[x];
                    o[0] = o[1] = o[2] = g; o[3] = 255; break; }
                case 2: { const uint8_t *s = row + (size_t)x * 3;
                    o[0] = s[0]; o[1] = s[1]; o[2] = s[2]; o[3] = 255; break; }
                case 4: { const uint8_t *s = row + (size_t)x * 2;
                    o[0] = o[1] = o[2] = s[0]; o[3] = s[1]; break; }
                case 6: { const uint8_t *s = row + (size_t)x * 4;
                    o[0] = s[0]; o[1] = s[1]; o[2] = s[2]; o[3] = s[3]; break; }
                case 3: {
                    /* Unpack the index from packed bits, MSB-first. */
                    unsigned idx;
                    if (depth == 8) {
                        idx = row[x];
                    } else {
                        unsigned bit = x * depth;
                        unsigned byte = row[bit >> 3];
                        unsigned shift = 8 - depth - (bit & 7);
                        idx = (byte >> shift) & ((1u << depth) - 1);
                    }
                    if ((int)idx >= pal_n) { rc = CONSOLE_PNG_ERR_PLTE; goto done; }
                    o[0] = palette[idx][0]; o[1] = palette[idx][1];
                    o[2] = palette[idx][2]; o[3] = pal_a[idx];
                    break; }
                }
            }
        }
    }

    out->w = w; out->h = h; out->rgba = rgba;
    rgba = NULL;
    rc = CONSOLE_PNG_OK;

done:
    free(idat);
    free(raw);
    free(rgba);
    return rc;
}

void console_image_free(console_image *img)
{
    if (!img) return;
    free(img->rgba);
    img->rgba = NULL;
    img->w = img->h = 0;
}
