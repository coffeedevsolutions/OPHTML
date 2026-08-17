// Intrinsic image sizing for <img> (backlog F3).
//
// Layout only needs width and height; decoding pixels is the baker's
// job (Pillow). PNG keeps the zero-dependency rule trivially: the
// IHDR chunk is mandatory, first, and at a fixed offset, so the
// dimensions are two big-endian u32s at bytes 16..24.
//
// PNG-only is a documented v0.2 limit — the baker rasterizes
// everything to GS texels anyway, so "convert your JPEG to PNG" is a
// build-machine constraint, not a shipping one.

import { readFileSync } from 'node:fs';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/**
 * Read a PNG's intrinsic size. Throws with a useful message for
 * missing files, non-PNG content, or a malformed header.
 */
export function readPngSize(path) {
  let buf;
  try {
    buf = readFileSync(path);
  } catch (err) {
    throw new Error(`image: cannot read "${path}": ${err.code ?? err.message}`);
  }
  if (buf.length < 24 || !buf.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error(
      `image: "${path}" is not a PNG — only PNG is supported at build time; `
      + 'convert other formats before compiling',
    );
  }
  if (buf.toString('ascii', 12, 16) !== 'IHDR') {
    throw new Error(`image: "${path}": malformed PNG (IHDR not first chunk)`);
  }
  const w = buf.readUInt32BE(16);
  const h = buf.readUInt32BE(20);
  if (w === 0 || h === 0) {
    throw new Error(`image: "${path}": zero-sized PNG`);
  }
  return { w, h };
}
