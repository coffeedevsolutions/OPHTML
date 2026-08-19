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
  const root = buildBoxTree(dom, sheet, null, null, warnings, null, {
    assetDir: options.assetDir ?? null,
  });
  if (!root) throw new Error('layout: root element is display: none');

  const ctx = { fonts };
  layoutTree(root, canvasW, canvasH, ctx);

  const { commands, focusables, slots } = buildDisplayList(root);
  const focus = solveFocusGraph(focusables, { wrap: options.focusWrap ?? false });
  for (const w of checkReachability(focus)) warnings.push(w);

  const lints = lintDocument(commands, focus, {
    canvasW, canvasH, par, ...options.lint,
  }).map((l) => `${l.rule}: ${l.message}`);

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
    commands,
    focus,
    slots,
    warnings: [...warnings, ...lints],
  };
}

/** Convenience: compile from file paths. <img> src attributes resolve
 * relative to the HTML file unless options.assetDir overrides. */
export function compileFiles(htmlPath, cssPath, options = {}) {
  return compile(
    readFileSync(htmlPath, 'utf8'),
    readFileSync(cssPath, 'utf8'),
    { assetDir: dirname(htmlPath), ...options },
  );
}
