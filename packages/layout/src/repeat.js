// Template expansion: `data-repeat` (backlog F6).
//
// A launcher lists things — saves, games, channels — and the count is a
// property of the data, not of the markup. Writing eight nearly identical
// rows by hand is how the channel-6 example ended up declaring seventeen
// slots and shipping a blob the runtime refused to load, because nothing
// about six copy-pasted tiles tells you how many you have.
//
// This runs on the element tree, before styles are computed, so a
// repeated element is indistinguishable from one that was typed out. It
// is deliberately *not* a loop over data: there is no data at build time.
// It stamps out N copies of a shape, and the app fills them at runtime
// through the slots inside.
//
// Substitution is explicit. `{i}` is the 0-based index and `{n}` is
// 1-based, in any attribute value and in text. Nothing is renamed behind
// your back: a `data-slot` without `{i}` produces N identical slot names,
// which `buildDisplayList` already rejects as a duplicate. That error is
// the right one to get, and it names the slot.

const MAX_REPEAT = 256;

/** Substitute {i} / {n} in a string. */
export function substituteIndex(s, i) {
  return s.replace(/\{(i|n)\}/g, (_, k) => String(k === 'i' ? i : i + 1));
}

function cloneWithIndex(el, i, TextNode, Element) {
  if (el.type === 'text') {
    return new TextNode(substituteIndex(el.text, i), el.line);
  }
  const attrs = {};
  for (const [k, v] of Object.entries(el.attrs)) {
    if (k === 'data-repeat') continue; // consumed here, never reaches CSS
    attrs[k] = substituteIndex(v, i);
  }
  const copy = new Element(el.tag, attrs, el.line);
  for (const child of el.children) {
    const c = cloneWithIndex(child, i, TextNode, Element);
    c.parent = copy;
    copy.children.push(c);
  }
  return copy;
}

function hasRepeat(el) {
  if (el.type !== 'element') return false;
  if ('data-repeat' in el.attrs) return true;
  return el.children.some(hasRepeat);
}

/**
 * Expand every `data-repeat` in place. Returns the number expanded, so
 * callers can report it; the tree is mutated.
 *
 * `Element` and `TextNode` are passed in rather than imported to keep
 * this module free of a cycle with html.js.
 */
export function expandRepeats(root, { Element, TextNode }, warnings = []) {
  if (root.type === 'element' && 'data-repeat' in root.attrs) {
    throw new Error(
      `layout: <${root.tag}> line ${root.line}: data-repeat on the root element `
      + 'has nothing to repeat into; put it on a child',
    );
  }
  let expanded = 0;

  const visit = (parent) => {
    const out = [];
    for (const child of parent.children) {
      if (child.type !== 'element' || !('data-repeat' in child.attrs)) {
        if (child.type === 'element') visit(child);
        out.push(child);
        continue;
      }
      const raw = child.attrs['data-repeat'];
      if (!/^\d+$/.test(raw)) {
        throw new Error(
          `layout: <${child.tag}> line ${child.line}: data-repeat="${raw}" is not `
          + 'a whole number. The count is baked, so it cannot come from data.',
        );
      }
      const count = parseInt(raw, 10);
      if (count < 1 || count > MAX_REPEAT) {
        throw new Error(
          `layout: <${child.tag}> line ${child.line}: data-repeat="${count}" is out `
          + `of range 1..${MAX_REPEAT}. Every copy costs commands, and a focusable `
          + 'one costs a focus node, so this is a budget you want to feel.',
        );
      }
      // Nested repeats would need a second index variable and a rule for
      // which {i} wins. Refuse rather than guess.
      if (child.children.some(hasRepeat)) {
        throw new Error(
          `layout: <${child.tag}> line ${child.line}: data-repeat inside data-repeat. `
          + 'Only one index is in scope, so the inner {i} would be ambiguous.',
        );
      }
      // Scan descendant *attributes* too, not just the repeated
      // element's own. The common shape puts {i} on a nested
      // data-slot and nothing on the row itself, which this warning
      // used to flag — on the pattern the README recommends.
      if (count > 1 && !/\{[in]\}/.test(serialise(child))) {
        warnings.push(
          `layout: <${child.tag}> line ${child.line}: data-repeat="${count}" but no `
          + '{i} or {n} anywhere inside, so every copy is identical. Add {i} to the '
          + 'ids and data-slot names, or the copies cannot be told apart.',
        );
      }
      for (let i = 0; i < count; i++) {
        const copy = cloneWithIndex(child, i, TextNode, Element);
        copy.parent = parent;
        visit(copy);
        out.push(copy);
      }
      expanded++;
    }
    parent.children = out;
  };

  visit(root);
  return expanded;
}

/** Everything an index could have been written into: this element's
 *  attributes and text, and every descendant's. */
function serialise(el) {
  if (el.type === 'text') return el.text;
  return Object.values(el.attrs).join('\u0000')
    + el.children.map(serialise).join('');
}
