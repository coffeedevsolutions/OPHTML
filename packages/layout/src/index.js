// @ps2ui/layout — public API.
//
// compile(html, css, options) → the ui.json intermediate representation.
// Everything the console must never do (parse, cascade, measure, wrap,
// solve) happens inside this call, on the build host.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { parseHTML, Element, TextNode } from './html.js';
import { parseStylesheet } from './css.js';
import { expandRepeats } from './repeat.js';
import { buildBoxTree, resetBoxIds } from './box.js';
import { layoutTree } from './flex.js';
import { buildDisplayList } from './paint.js';
import { solveFocusGraph, checkReachability } from './focus.js';
import { lintDocument } from './lint.js';
import { loadFont } from './text.js';
import { pixelAspect, displaySize } from './aspect.js';

export { parseHTML } from './html.js';
export { expandRepeats, substituteIndex } from './repeat.js';
export { parseStylesheet, computeStyle, INITIAL_STYLE } from './css.js';
export { wrapText, ellipsize, loadFont, Font, clearFontCache } from './text.js';
export { measureNode, computeFlexLines, placeNode } from './flex.js';
export { buildBoxTree, walkBoxes, resetBoxIds } from './box.js';
export { solveFocusGraph } from './focus.js';
export { lintDocument, DEFAULT_LINT_OPTIONS } from './lint.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const DEFAULT_FONT_DIR = join(HERE, '..', '..', '..', 'fonts');

export const IR_VERSION = 1;

/**
 * Font context: maps a CSS font-weight to loaded metrics.
 * Regular (<600) and bold (>=600) faces; the PS2 target does not carry
 * enough VRAM for a full weight axis.
 */
export class FontContext {
  constructor({ regular, bold }) {
    this.regular = regular;
    this.bold = bold ?? regular;
  }
  resolve(weight) {
    return weight >= 600 ? this.bold : this.regular;
  }
  static fromDir(dir = DEFAULT_FONT_DIR) {
    return new FontContext({
      regular: loadFont(join(dir, 'default.metrics.json')),
      bold: loadFont(join(dir, 'default-bold.metrics.json')),
    });
  }
}

/**
 * Compile HTML + CSS strings into the IR.
 *
 * options:
 *   canvasW/canvasH — target resolution (default 640x448 NTSC)
 *   fonts           — FontContext (default: repo fonts/)
 *   lint            — lint option overrides
 */
export function compile(htmlSrc, cssSrc, options = {}) {
  const canvasW = options.canvasW ?? 640;
  const canvasH = options.canvasH ?? 448;
  // The panel's aspect, which is not the framebuffer's. Default 4:3.
  const displayAspect = options.displayAspect ?? [4, 3];
  const par = pixelAspect(canvasW, canvasH, displayAspect);
  const fonts = options.fonts ?? FontContext.fromDir(options.fontDir);
  const warnings = [];

  const dom = parseHTML(htmlSrc);
  // Stamp out data-repeat templates before anything computes styles, so
  // a repeated row is indistinguishable from one that was typed out.
  expandRepeats(dom, { Element, TextNode }, warnings);
  const sheet = parseStylesheet(cssSrc);
  warnings.push(...sheet.warnings);

  resetBoxIds();
  const boxEnv = { assetDir: options.assetDir ?? null };
  const root = buildBoxTree(dom, sheet, null, null, warnings, null, boxEnv);
  if (!root) throw new Error('layout: root element is display: none');
  if (boxEnv.undirected) {
    // All of them at once: a document written against the old implicit
    // default has one of these per container, and reporting the first
    // would make migration a queue of single-line fixes.
    throw new Error(
      `layout: ${boxEnv.undirected.length} container(s) lay out two or more `
      + 'children without stating flex-direction:\n'
      // Sorted: the tree is walked children-first, so unsorted this
      // reads bottom-up and an author fixes their file backwards.
      + boxEnv.undirected.sort((a, b) => a.line - b.line)
          .map((u) => u.text).join('\n')
      + "\nThere is no default. CSS's initial value is row, ps2ui once used "
      + 'column, so either silent answer is wrong for half of all authors — '
      + 'add flex-direction: row or column to each.',
    );
  }

  const ctx = { fonts };
  layoutTree(root, canvasW, canvasH, ctx);

  const themeNames = sheet.themeNames ?? ['root'];
  const { commands, focusables, slots, forLint } = buildDisplayList(
    root, themeNames.length);
  const focus = solveFocusGraph(focusables, { wrap: options.focusWrap ?? false });
  for (const w of checkReachability(focus)) warnings.push(w);

  // THE LINTS RUN OVER EVERY THEME, NOT JUST THE DEFAULT ROW.
  //
  // contrast and ntsc-red-bleed read colours; everything else reads
  // geometry. A theme moves colours and nothing else, so a UI that is
  // readable in :root can be unreadable in @theme light and every
  // check in this repository would still pass -- the blob is correct,
  // the screenshots are correct for the row they render, and the
  // failure is discovered on a television. That is exactly the class
  // of defect this phase exists to close, arriving through the feature
  // built to close it.
  //
  // Deduplicated BY RULE, not by message. The geometry lints produce
  // byte-identical strings in every row and would otherwise be
  // reported n_theme times, which teaches people to skim the list --
  // the same argument data-nocontrast makes in lint.js. The colour
  // lints are never deduplicated at all.
  //
  // The first version deduplicated by message and justified it with
  // "a colour lint that fires in two themes carries a different ratio
  // in each, so it survives". That is not a truth about contrast.
  // contrastRatio is SYMMETRIC in (foreground, background), so two
  // themes that swap the pair produce the identical string:
  //
  //     :root        { --panel: #808080; --ink: #858585 }
  //     @theme light { --panel: #858585; --ink: #808080 }
  //
  // Both fail at 1.07:1, one message, and nothing names the light
  // theme. Rounding to two decimals widens it well past the symmetric
  // case -- any two pairs landing on the same 2dp ratio collapse.
  //
  // Not silent, since row 0 still reports it, but it costs a round
  // trip: fix :root, rebuild, and only then discover light was broken
  // too. The lint's own `rule` field already carries the distinction
  // this comment was drawing in prose, so use it.
  const lintOpts = { canvasW, canvasH, par, ...options.lint };
  // forLint, not commands: it is the same list with slot text spliced
  // in at the index it would have painted at. A data-slot draws no
  // static command, so linting `commands` checked every colour in the
  // document EXCEPT the dynamic text -- 127 of them in opl-env.
  const lints = lintDocument(forLint, focus, lintOpts)
    .map((l) => `${l.rule}: ${l.message}`);
  const seen = new Set(lints);
  for (let t = 1; t < themeNames.length; t++) {
    for (const l of lintDocument(commandsInTheme(forLint, t), focus, lintOpts)) {
      const line = `${l.rule}: ${l.message}`;
      if (!COLOUR_LINTS.has(l.rule)) {
        if (seen.has(line)) continue;
        seen.add(line);
      }
      lints.push(`@theme ${themeNames[t]}: ${line}`);
    }
  }

  return {
    version: IR_VERSION,
    canvas: {
      w: canvasW,
      h: canvasH,
      // Authored display aspect as an exact ratio; par is derived and
      // carried for consumers that would otherwise recompute it.
      displayAspect,
      par: Math.round(par * 10000) / 10000,
      display: displaySize(canvasW, canvasH, displayAspect),
    },
    fonts: {
      regular: { family: fonts.regular.family, weight: fonts.regular.weight },
      bold: { family: fonts.bold.family, weight: fonts.bold.weight },
    },
    // THE THEME LIST, INDEX-ORDERED, ROOT FIRST. Names are build-time
    // only: the blob stores n_theme and `ps2ui_theme_set` selects by
    // index, so this exists so a human (and ps2ui-check) can say which
    // index they meant. Length is the width of every *Themes vector in
    // the command list and slot table.
    themes: themeNames,
    commands,
    focus,
    slots,
    warnings: [...warnings, ...lints],
  };
}

/** Convenience: compile from file paths. <img> src attributes resolve
 * relative to the HTML file unless options.assetDir overrides. */
// The lints that read colour. A theme moves colour and nothing else,
// so these are exactly the ones whose result can differ per row -- and
// exactly the ones that must never be deduplicated against row 0,
// because two rows can fail identically for different reasons.
const COLOUR_LINTS = new Set(['contrast', 'ntsc-red-bleed']);

/** The display list as theme `t` paints it.
 *
 * Colour only: a theme cannot move geometry, so x/y/w/h and every
 * structural field are shared by reference and the copy is shallow.
 * Falls back to the row-0 value when a command carries no vector,
 * which is the untinted art whose colour is in its texels.
 */
function commandsInTheme(commands, t) {
  return commands.map((c) => {
    if (!c.fillThemes && !c.borderColorThemes && !c.colorThemes) return c;
    const out = { ...c };
    if (c.fillThemes) out.fill = c.fillThemes[t];
    if (c.borderColorThemes) out.borderColor = c.borderColorThemes[t];
    if (c.colorThemes) out.color = c.colorThemes[t];
    return out;
  });
}

export function compileFiles(htmlPath, cssPath, options = {}) {
  return compile(
    readFileSync(htmlPath, 'utf8'),
    readFileSync(cssPath, 'utf8'),
    { assetDir: dirname(htmlPath), ...options },
  );
}
