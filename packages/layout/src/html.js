// A small, forgiving HTML parser producing an element tree.
//
// This is not a general web parser: ps2ui documents are authored, not
// scraped, so the parser accepts the well-formed subset and reports
// anything else as a hard error with a line number. Silent recovery is
// how you end up debugging layout output instead of your markup.

const VOID_ELEMENTS = new Set(['br', 'hr', 'img', 'input', 'meta', 'link']);

export class Element {
  constructor(tag, attrs, line) {
    this.type = 'element';
    this.tag = tag;
    this.attrs = attrs;
    this.children = [];
    this.parent = null;
    this.line = line;
  }
  get id() { return this.attrs.id ?? null; }
  get classes() {
    return (this.attrs.class ?? '').split(/\s+/).filter(Boolean);
  }
}

export class TextNode {
  constructor(text, line) {
    this.type = 'text';
    this.text = text;
    this.parent = null;
    this.line = line;
  }
}

class Reader {
  constructor(src) {
    this.src = src;
    this.pos = 0;
    this.line = 1;
  }
  eof() { return this.pos >= this.src.length; }
  peek(n = 0) { return this.src[this.pos + n]; }
  startsWith(s) { return this.src.startsWith(s, this.pos); }
  advance(n = 1) {
    for (let i = 0; i < n && this.pos < this.src.length; i++) {
      if (this.src[this.pos] === '\n') this.line++;
      this.pos++;
    }
  }
  error(msg) {
    throw new Error(`html: line ${this.line}: ${msg}`);
  }
}

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', middot: '·', hellip: '…' };

export function decodeEntities(s) {
  return s.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (m, body) => {
    if (body[0] === '#') {
      const code = body[1] === 'x' || body[1] === 'X'
        ? parseInt(body.slice(2), 16)
        : parseInt(body.slice(1), 10);
      return Number.isNaN(code) ? m : String.fromCodePoint(code);
    }
    return ENTITIES[body] ?? m;
  });
}

function parseAttrs(r) {
  const attrs = {};
  for (;;) {
    while (!r.eof() && /\s/.test(r.peek())) r.advance();
    if (r.eof()) r.error('unexpected end of input in tag');
    if (r.peek() === '>' || r.startsWith('/>')) return attrs;
    let name = '';
    while (!r.eof() && /[^\s=/>]/.test(r.peek())) { name += r.peek(); r.advance(); }
    if (!name) r.error('malformed attribute');
    name = name.toLowerCase();
    while (!r.eof() && /\s/.test(r.peek())) r.advance();
    if (r.peek() !== '=') { attrs[name] = ''; continue; }
    r.advance();
    while (!r.eof() && /\s/.test(r.peek())) r.advance();
    const quote = r.peek();
    if (quote !== '"' && quote !== "'") r.error(`attribute ${name} must be quoted`);
    r.advance();
    let value = '';
    while (!r.eof() && r.peek() !== quote) { value += r.peek(); r.advance(); }
    if (r.eof()) r.error(`unterminated attribute ${name}`);
    r.advance();
    attrs[name] = decodeEntities(value);
  }
}

/**
 * Parse an HTML document (or fragment) into a single root Element.
 * A full document contributes its <body>; a fragment gets a synthetic
 * root so callers always receive exactly one element.
 */
export function parseHTML(src) {
  const r = new Reader(src);
  const root = new Element('#root', {}, 1);
  const stack = [root];
  let textStart = null;
  let textBuf = '';
  let textLine = 1;

  const flushText = () => {
    if (textBuf) {
      // Collapse whitespace runs the way CSS normal white-space does.
      const collapsed = decodeEntities(textBuf).replace(/\s+/g, ' ');
      if (collapsed.trim() !== '') {
        const node = new TextNode(collapsed, textLine);
        node.parent = stack[stack.length - 1];
        stack[stack.length - 1].children.push(node);
      }
    }
    textBuf = '';
    textStart = null;
  };

  while (!r.eof()) {
    if (r.startsWith('<!--')) {
      // Comments are invisible: they must not split "a<!-- -->b" into
      // two text nodes, so no flushText here.
      const end = r.src.indexOf('-->', r.pos);
      if (end === -1) r.error('unterminated comment');
      r.advance(end + 3 - r.pos);
      continue;
    }
    if (r.startsWith('<!')) { // doctype
      flushText();
      while (!r.eof() && r.peek() !== '>') r.advance();
      r.advance();
      continue;
    }
    if (r.startsWith('</')) {
      flushText();
      r.advance(2);
      let tag = '';
      while (!r.eof() && r.peek() !== '>') { tag += r.peek(); r.advance(); }
      r.advance();
      tag = tag.trim().toLowerCase();
      if (tag === 'html' || tag === 'body') continue; // transparent wrappers
      const top = stack[stack.length - 1];
      if (top === root) r.error(`closing </${tag}> with no open element`);
      if (top.tag !== tag) r.error(`closing </${tag}> but <${top.tag}> (line ${top.line}) is open`);
      stack.pop();
      continue;
    }
    if (r.peek() === '<') {
      flushText();
      const tagLine = r.line;
      r.advance();
      let tag = '';
      while (!r.eof() && /[a-zA-Z0-9-]/.test(r.peek())) { tag += r.peek(); r.advance(); }
      if (!tag) r.error('bare "<" in content; write &lt;');
      tag = tag.toLowerCase();
      const attrs = parseAttrs(r);
      let selfClose = false;
      if (r.startsWith('/>')) { selfClose = true; r.advance(2); }
      else if (r.peek() === '>') r.advance();
      else r.error(`malformed tag <${tag}>`);

      if (tag === 'head' || tag === 'style' || tag === 'script' || tag === 'title') {
        // Skip non-layout subtrees entirely (external CSS is the contract).
        const close = `</${tag}`;
        const idx = r.src.toLowerCase().indexOf(close, r.pos);
        if (idx === -1) r.error(`unterminated <${tag}>`);
        r.advance(idx - r.pos);
        const gt = r.src.indexOf('>', r.pos);
        r.advance(gt + 1 - r.pos);
        continue;
      }
      if (tag === 'html' || tag === 'body') continue; // transparent wrappers

      const el = new Element(tag, attrs, tagLine);
      el.parent = stack[stack.length - 1];
      stack[stack.length - 1].children.push(el);
      if (!selfClose && !VOID_ELEMENTS.has(tag)) stack.push(el);
      continue;
    }
    if (textStart === null) { textStart = r.pos; textLine = r.line; }
    textBuf += r.peek();
    r.advance();
  }
  flushText();
  if (stack.length > 1) {
    const top = stack[stack.length - 1];
    throw new Error(`html: <${top.tag}> opened on line ${top.line} is never closed`);
  }
  // A document with a single root element is common; unwrap the synthetic
  // root only when it adds nothing.
  if (root.children.length === 1 && root.children[0].type === 'element') {
    const only = root.children[0];
    only.parent = null;
    return only;
  }
  return root;
}

/** Depth-first walk over elements and text nodes. */
export function walk(node, fn) {
  fn(node);
  if (node.children) for (const c of node.children) walk(c, fn);
}
