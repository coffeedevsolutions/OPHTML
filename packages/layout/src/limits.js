/**
 * Hard caps on what a stylesheet and a screen may ask for (S3).
 *
 * WHY THIS EXISTS. A theme is a file somebody else wrote. The compilers
 * accepted whatever it asked for, and three of the four requests S3
 * names cost real time or memory before anything refused them:
 *
 *   - `--canvas 30000x30000` compiled clean, exit 0, and wrote IR. The
 *     bake refused it with a good message -- two framebuffers at that
 *     size need 7207682048 B of 4194304 B -- and then
 *     `--vram-budget 999999999` walked straight past it and wrote a
 *     17760-byte blob, because the budget charges TEXTURES and a
 *     framebuffer is not a texture. The message said "a narrower canvas
 *     is the only fix" while the documented override was the other one.
 *
 *   - Nesting had no cap. 1000 deep compiled; 2000 deep died with
 *     `error: Maximum call stack size exceeded`, which is V8's stack
 *     rather than a decision, so the real limit moves with the machine
 *     and the message names neither the element nor a number.
 *
 *   - Node count had no cap. 100000 boxes compiled in 5.2s to 39 MB of
 *     IR, exit 0, growing linearly. Nothing was wrong; nothing was
 *     bounded either.
 *
 * THE NUMBERS ARE DERIVED FROM THE SHIPPED CORPUS, NOT CHOSEN. Measured
 * across all 17 screens in examples/ and fixtures/ with THIS FILE'S OWN
 * checkTree, after expandRepeats: the largest is 93 elements at depth
 * 5 (examples/opl-env/ui/library.html), and every supported mode is
 * 640x448 or 640x512. The first version of this paragraph said 90 at
 * depth 8, from a regex over raw HTML that counted void elements and
 * did not expand repeats -- a different population, measured with a
 * different instrument than the one the cap uses. Review of #166
 * caught it.
 *
 * So each cap sits an order of magnitude above the biggest real thing:
 *
 *   canvas 2048   the GS framebuffer maximum per dimension, 3.2x the
 *                 tallest mode. A cap here cannot be the VRAM budget,
 *                 because that is the thing the override moves.
 *   nodes  10000  ~108x the largest expanded screen, and it bounds
 *                 the IR at roughly 4 MB. data-repeat multiplies, so
 *                 the count is taken AFTER expansion. The ratio is
 *                 generous because the IR size, not the corpus, is
 *                 what 10000 was chosen against.
 *   depth  64     ~13x the deepest shipped screen and far under the
 *                 ~1500 where V8 gives out, so the refusal is this
 *                 file's rather than the interpreter's.
 *
 * THEY FAIL RATHER THAN WARN, which is the opposite of what
 * check-doc-impact.py argues for itself and right for the same reason.
 * A warning is correct where the work might be fine -- a change can be
 * doc-neutral. None of these can: a PS2 cannot display a 30000px
 * canvas, so there is no version of that request that is correct work
 * somebody would want an exemption for.
 *
 * AND EVERY ONE IS OVERRIDABLE, in the project file beside vramBudget.
 * A cap with no escape gets edited out of the source by the first
 * person it blocks, which is worse than a cap with a documented one.
 */

export const LIMITS = {
  canvasDim: 2048,
  nodes: 10000,
  depth: 64,
};

/** The limits, with any caller overrides validated and applied. */
export function resolveLimits(over) {
  const out = { ...LIMITS };
  for (const [key, value] of Object.entries(over || {})) {
    if (!(key in LIMITS)) {
      throw new Error(
        `limits: unknown limit ${JSON.stringify(key)}. `
        + `Known: ${Object.keys(LIMITS).join(', ')}`);
    }
    if (!Number.isInteger(value) || value < 1) {
      throw new Error(
        `limits: ${key} must be a positive integer, got `
        + `${JSON.stringify(value)}`);
    }
    out[key] = value;
  }
  return out;
}

/**
 * Refuse a canvas the hardware cannot scan out.
 *
 * Checked in the LAYOUT compiler rather than only at bake time,
 * because the bake is where the good message already lives and it
 * arrives after a full layout pass -- and because the bake's version
 * of it is charged against a budget a flag can raise.
 */
export function checkCanvas(w, h, limits) {
  for (const [name, value] of [['width', w], ['height', h]]) {
    if (!Number.isInteger(value) || value < 1) {
      throw new Error(
        `layout: canvas ${name} must be a positive integer, got `
        + `${JSON.stringify(value)}`);
    }
    if (value > limits.canvasDim) {
      throw new Error(
        `layout: canvas ${name} ${value} exceeds ${limits.canvasDim}, `
        + 'the largest framebuffer dimension the GS can scan out. '
        + 'Every supported mode is 640x448 or 640x512; --mode picks '
        + 'one. Raise "limits": {"canvasDim": N} in the project file '
        + 'if you are targeting something this does not know about.');
    }
  }
}

/**
 * Refuse a tree too large or too deep, and name where it went wrong.
 *
 * ITERATIVE ON PURPOSE. A recursive walk to find the depth that breaks
 * a recursive walk overflows before it can report anything, which is
 * the failure this replaces.
 */
export function checkTree(root, limits) {
  let nodes = 0;
  let deepest = 0;
  let deepestEl = null;
  const stack = [[root, 0]];
  while (stack.length) {
    const [node, depth] = stack.pop();
    if (node.children === undefined) continue;   // a text node
    nodes += 1;
    if (depth > deepest) { deepest = depth; deepestEl = node; }
    if (nodes > limits.nodes) {
      throw new Error(
        `layout: more than ${limits.nodes} elements after data-repeat `
        + 'expansion. The largest screen shipped with ps2ui is 93, and '
        + 'a PS2 draws one record per box, so this is a runaway repeat '
        + 'or a generated file. Raise "limits": {"nodes": N} in the '
        + 'project file if it is neither.');
    }
    for (const kid of node.children) stack.push([kid, depth + 1]);
  }
  if (deepest > limits.depth) {
    const where = deepestEl && deepestEl.line
      ? ` (deepest at line ${deepestEl.line})` : '';
    throw new Error(
      `layout: elements nested ${deepest} deep${where}, past the limit `
      + `of ${limits.depth}. The deepest screen shipped with ps2ui is `
      + '5. Past about 1500 the compiler runs out of stack and reports '
      + 'nothing useful, which is what this exists to get in front of. '
      + 'Raise "limits": {"depth": N} in the project file if you mean '
      + 'it.');
  }
  return { nodes, depth: deepest };
}
