#!/usr/bin/env node
// ps2ui-dev — the edit loop (backlog F11).
//
//   ps2ui-dev <page.html> <page.css> -o <outdir>
//             [--mode ntsc|pal] [--canvas WxH] [--font-dir DIR]
//             [--focus-wrap] [--montage] [--palettize-images] [--once]
//
// Watches the HTML, the CSS, and the HTML's directory (assets/ lives
// there), recompiles on change, bakes, and refreshes outdir/preview.png.
// Layout runs in-process; the baker is spawned (python3 -m ps2ui_bake).
// --once builds a single time and exits — that is what CI smoke-tests.

import { watch, mkdirSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { compileFiles } from '../src/index.js';

function usage(code) {
  console.error('usage: ps2ui-dev <page.html> <page.css> -o <outdir> '
    + '[--mode ntsc|pal] [--canvas WxH] [--font-dir DIR] [--focus-wrap] '
    + '[--montage] [--palettize-images] [--once]');
  process.exit(code);
}

import { MODES, parseAspect } from '../src/aspect.js';

const args = process.argv.slice(2);
const positional = [];
let outDir = null;
let mode = null;
let aspectArg = null;
let canvas = null;
let fontDir;
let focusWrap = false;
let montage = false;
let palettize = false;
let once = false;

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '-o': outDir = args[++i]; break;
    case '--mode': mode = args[++i]; break;
    case '--display-aspect': aspectArg = args[++i]; break;
    case '--canvas': canvas = args[++i]; break;
    case '--font-dir': fontDir = args[++i]; break;
    case '--focus-wrap': focusWrap = true; break;
    case '--montage': montage = true; break;
    case '--palettize-images': palettize = true; break;
    case '--once': once = true; break;
    case '-h': case '--help': usage(0); break;
    default: positional.push(args[i]);
  }
}
if (positional.length !== 2 || !outDir) usage(2);

const [htmlPath, cssPath] = positional.map((p) => resolve(p));
mkdirSync(outDir, { recursive: true });

const options = { fontDir, focusWrap };
if (mode) {
  if (!(mode in MODES)) usage(2);
  options.canvasW = MODES[mode].w;
  options.canvasH = MODES[mode].h;
  options.displayAspect = MODES[mode].aspect;
}
if (aspectArg) options.displayAspect = parseAspect(aspectArg);
if (canvas) {
  const m = /^(\d+)x(\d+)$/.exec(canvas);
  if (!m) usage(2);
  options.canvasW = parseInt(m[1], 10);
  options.canvasH = parseInt(m[2], 10);
}

const HERE = dirname(fileURLToPath(import.meta.url));
const BAKER_DIR = join(HERE, '..', '..', 'baker');

function build() {
  const started = Date.now();
  let ir;
  try {
    ir = compileFiles(htmlPath, cssPath, options);
  } catch (err) {
    console.error(`\x1b[31mlayout error:\x1b[0m ${err.message}`);
    return false;
  }
  const irPath = join(outDir, 'ui.json');
  writeFileSync(irPath, JSON.stringify(ir, null, 1));

  const bakeArgs = ['-m', 'ps2ui_bake', irPath,
    '-o', join(outDir, 'ui.uib'),
    '--preview', join(outDir, 'preview.png')];
  if (montage) bakeArgs.push('--montage', join(outDir, 'states.png'));
  if (palettize) bakeArgs.push('--palettize-images');
  const bake = spawnSync('python3', bakeArgs, {
    stdio: ['ignore', 'inherit', 'inherit'],
    env: { ...process.env, PYTHONPATH: BAKER_DIR },
  });
  if (bake.status !== 0) {
    console.error('\x1b[31mbake failed\x1b[0m');
    return false;
  }
  const nWarn = ir.warnings.length;
  console.error(`\x1b[32mbuilt\x1b[0m in ${Date.now() - started}ms — `
    + `${ir.commands.length} commands, ${ir.focus.nodes.length} focusables, `
    + `${nWarn} warning${nWarn === 1 ? '' : 's'} -> ${outDir}/preview.png`);
  for (const w of ir.warnings) console.error(`  warning: ${w}`);
  return true;
}

const ok = build();
if (once) process.exit(ok ? 0 : 1);

// Watch the two named files plus the HTML's directory, which is where
// assets/ lives by convention. fs.watch fires in bursts; debounce.
let timer = null;
const trigger = (what) => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    console.error(`\x1b[2m${what} changed\x1b[0m`);
    build();
  }, 120);
};
for (const target of new Set([htmlPath, cssPath, dirname(htmlPath)])) {
  try {
    watch(target, { recursive: true }, (_ev, file) => trigger(file ?? target));
  } catch {
    watch(target, (_ev, file) => trigger(file ?? target)); // no recursive on some platforms
  }
}
console.error(`watching ${dirname(htmlPath)} — ctrl-c to stop`);
