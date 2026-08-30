#!/usr/bin/env node
// ps2ui-layout <page.html> <page.css> -o ui.json [--canvas 640x448] [--font-dir DIR] [--strict] [--min-font-size PX]
//
// --strict promotes warnings (including CRT lints) to a non-zero exit.

import { writeFileSync } from 'node:fs';
import { compileFiles } from '../src/index.js';
import { MODES, parseAspect } from '../src/aspect.js';


function usage(code) {
  console.error('usage: ps2ui-layout <page.html> <page.css> -o <ui.json> '
    + '[--mode ntsc|ntsc16x9|pal|pal16x9] [--display-aspect W:H] [--canvas WxH] [--font-dir DIR] [--focus-wrap] [--strict] [--min-font-size PX]');
  process.exit(code);
}


const args = process.argv.slice(2);
const positional = [];
let out = null;
let canvas = null;
let mode = null;
let aspectArg = null;
let fontDir;
let strict = false;
let minFontSize = null;
let focusWrap = false;

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '-o': out = args[++i]; break;
    case '--canvas': canvas = args[++i]; break;
    case '--mode': mode = args[++i]; break;
    case '--display-aspect': aspectArg = args[++i]; break;
    case '--font-dir': fontDir = args[++i]; break;
    case '--focus-wrap': focusWrap = true; break;
    case '--strict': strict = true; break;
    // A DELIBERATE FLOOR, WRITTEN DOWN. The default 14px is the couch
    // rule; a document that means to go below it has to say so here
    // rather than have the rule quietly not reach its text.
    case '--min-font-size': minFontSize = parseInt(args[++i], 10); break;
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
  options.displayAspect = MODES[mode].aspect;
}
if (aspectArg) options.displayAspect = parseAspect(aspectArg); // beats --mode
if (minFontSize !== null) {
  if (!Number.isFinite(minFontSize) || minFontSize <= 0) {
    console.error('ps2ui-layout: --min-font-size takes a positive integer');
    process.exit(2);
  }
  options.lint = { ...(options.lint || {}), minFontSize };
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
  // Every op in the IR paints -- rect, text and image are the whole
  // set. Counting only rect and text reported "0 paint commands"
  // for a page of nothing but images, which reads as "nothing was
  // drawn" and cost two false starts while streamed slots were
  // being built.
  const quads = ir.commands.length;
  console.error(`ps2ui-layout: ${quads} paint commands, ${ir.focus.nodes.length} focusables -> ${out}`);
  if (strict && ir.warnings.length > 0) {
    console.error(`ps2ui-layout: --strict: ${ir.warnings.length} warning(s)`);
    process.exit(1);
  }
} catch (err) {
  console.error(`error: ${err.message}`);
  process.exit(1);
}
