#!/usr/bin/env node
// ps2ui-layout <page.html> <page.css> -o ui.json [--canvas 640x448] [--font-dir DIR] [--strict]
//
// --strict promotes warnings (including CRT lints) to a non-zero exit.

import { writeFileSync } from 'node:fs';
import { compileFiles } from '../src/index.js';

function usage(code) {
  console.error('usage: ps2ui-layout <page.html> <page.css> -o <ui.json> '
    + '[--mode ntsc|pal] [--canvas WxH] [--font-dir DIR] [--focus-wrap] [--strict]');
  process.exit(code);
}

// Video-mode presets: canvas size drives layout AND the CRT linter's
// safe-area math (5% of canvas). The runtime side of PAL is your
// gsKit init (GS_MODE_PAL) — the blob itself is mode-agnostic.
const MODES = {
  ntsc: { w: 640, h: 448 },
  pal: { w: 640, h: 512 },
};

const args = process.argv.slice(2);
const positional = [];
let out = null;
let canvas = null;
let mode = null;
let fontDir;
let strict = false;
let focusWrap = false;

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '-o': out = args[++i]; break;
    case '--canvas': canvas = args[++i]; break;
    case '--mode': mode = args[++i]; break;
    case '--font-dir': fontDir = args[++i]; break;
    case '--focus-wrap': focusWrap = true; break;
    case '--strict': strict = true; break;
    case '-h': case '--help': usage(0); break;
    default: positional.push(args[i]);
  }
}
if (positional.length !== 2 || !out) usage(2);

const options = { fontDir, focusWrap };
if (mode) {
  if (!(mode in MODES)) usage(2);
  options.canvasW = MODES[mode].w;
  options.canvasH = MODES[mode].h;
}
if (canvas) { // explicit --canvas beats --mode
  const m = /^(\d+)x(\d+)$/.exec(canvas);
  if (!m) usage(2);
  options.canvasW = parseInt(m[1], 10);
  options.canvasH = parseInt(m[2], 10);
}

try {
  const ir = compileFiles(positional[0], positional[1], options);
  for (const w of ir.warnings) console.warn(`warning: ${w}`);
  writeFileSync(out, JSON.stringify(ir, null, 1));
  const quads = ir.commands.filter((c) => c.op === 'rect' || c.op === 'text').length;
  console.error(`ps2ui-layout: ${quads} paint commands, ${ir.focus.nodes.length} focusables -> ${out}`);
  if (strict && ir.warnings.length > 0) {
    console.error(`ps2ui-layout: --strict: ${ir.warnings.length} warning(s)`);
    process.exit(1);
  }
} catch (err) {
  console.error(`error: ${err.message}`);
  process.exit(1);
}
