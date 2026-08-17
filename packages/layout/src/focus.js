// Spatial focus-graph solver.
//
// The console has a D-pad, not a pointer. At build time every focusable
// box becomes a node, and for each of the four directions we solve "if
// the user presses right while here, where do they land?" — so the
// runtime does a table lookup, never geometry.
//
// The metric is the classic beam-then-distance heuristic:
//   1. Candidates must make progress in the pressed direction (their
//      center is strictly beyond the current center on that axis).
//   2. Candidates overlapping the moving box's perpendicular extent
//      ("in the beam") beat all candidates outside it.
//   3. Ties break by Euclidean distance between centers, weighted 2:1
//      in favor of the perpendicular axis staying put — pressing right
//      should not diagonal-jump a whole row when a same-row target
//      exists slightly farther away.

function center(box) {
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

function overlap1D(a0, a1, b0, b1) {
  return Math.min(a1, b1) - Math.max(a0, b0) > 0;
}

const DIRS = ['up', 'down', 'left', 'right'];

function findTarget(from, candidates, dir) {
  const fc = center(from);
  let best = null;
  let bestKey = null;
  for (const cand of candidates) {
    if (cand === from) continue;
    const cc = center(cand);
    const dx = cc.x - fc.x;
    const dy = cc.y - fc.y;
    let progress;
    let inBeam;
    let perp;
    switch (dir) {
      case 'right': progress = dx > 0; perp = Math.abs(dy); inBeam = overlap1D(from.y, from.y + from.height, cand.y, cand.y + cand.height); break;
      case 'left': progress = dx < 0; perp = Math.abs(dy); inBeam = overlap1D(from.y, from.y + from.height, cand.y, cand.y + cand.height); break;
      case 'down': progress = dy > 0; perp = Math.abs(dx); inBeam = overlap1D(from.x, from.x + from.width, cand.x, cand.x + cand.width); break;
      case 'up': progress = dy < 0; perp = Math.abs(dx); inBeam = overlap1D(from.x, from.x + from.width, cand.x, cand.x + cand.width); break;
      default: throw new Error(`bad direction ${dir}`);
    }
    if (!progress) continue;
    const along = dir === 'left' || dir === 'right' ? Math.abs(dx) : Math.abs(dy);
    const key = [
      inBeam ? 0 : 1,          // beam candidates first
      along + 2 * perp,        // then weighted distance
      cand.id,                 // then document order, for determinism
    ];
    if (bestKey === null
      || key[0] < bestKey[0]
      || (key[0] === bestKey[0] && key[1] < bestKey[1] - 1e-9)
      || (key[0] === bestKey[0] && Math.abs(key[1] - bestKey[1]) <= 1e-9 && key[2] < bestKey[2])) {
      best = cand;
      bestKey = key;
    }
  }
  return best;
}

const OPPOSITE = { up: 'down', down: 'up', left: 'right', right: 'left' };

/**
 * Wrap target for a dead-end direction: the farthest in-beam candidate
 * on the opposite side, so pressing right off the row's end lands on
 * its leftmost member. Solved here at build time — wrap edges are just
 * ordinary graph edges to the runtime.
 */
function findWrapTarget(from, candidates, dir) {
  let best = null;
  let bestKey = null;
  for (const cand of candidates) {
    if (cand === from) continue;
    const inBeam = dir === 'left' || dir === 'right'
      ? overlap1D(from.y, from.y + from.height, cand.y, cand.y + cand.height)
      : overlap1D(from.x, from.x + from.width, cand.x, cand.x + cand.width);
    if (!inBeam) continue;
    const fc = center(from);
    const cc = center(cand);
    const delta = dir === 'left' || dir === 'right' ? cc.x - fc.x : cc.y - fc.y;
    // Wrapping right seeks the farthest candidate to the LEFT, etc.
    const wantNegative = dir === 'right' || dir === 'down';
    if (wantNegative ? delta >= 0 : delta <= 0) continue;
    const key = [Math.abs(delta), -cand.id];
    if (bestKey === null || key[0] > bestKey[0]
      || (key[0] === bestKey[0] && key[1] > bestKey[1])) {
      best = cand;
      bestKey = key;
    }
  }
  return best;
}

/**
 * Solve the focus graph for a set of focusable boxes.
 * Returns { nodes, initial } where nodes is an array of
 *   { id, name, rect, up, down, left, right }  (neighbor ids or null)
 * ordered by document order. `initial` is the box carrying the
 * `autofocus` attribute, else the first focusable in document order.
 *
 * options.wrap: fill dead-end directions with wrap-around edges
 * (per-axis, in-beam only — pressing right on the last tile of a row
 * wraps to that row's first tile, never to another row).
 */
export function solveFocusGraph(focusables, options = {}) {
  const list = [...focusables.values()];
  const nodes = list.map((box) => {
    const node = {
      id: box.id,
      name: box.el.id ?? box.el.attrs.name ?? `box${box.id}`,
      rect: [box.x, box.y, box.width, box.height],
    };
    for (const dir of DIRS) {
      let target = findTarget(box, list, dir);
      if (!target && options.wrap) target = findWrapTarget(box, list, dir);
      node[dir] = target ? target.id : null;
    }
    return node;
  });

  let initial = null;
  for (const box of list) {
    if ('autofocus' in box.el.attrs) { initial = box.id; break; }
  }
  if (initial === null && list.length > 0) initial = list[0].id;

  return { nodes, initial };
}

/**
 * Sanity pass over the solved graph: every focusable should be reachable
 * from the initial node, or D-pad users can never select it. Returns
 * warning strings.
 */
export function checkReachability(graph) {
  const warnings = [];
  if (graph.initial === null) return warnings;
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const seen = new Set([graph.initial]);
  const queue = [graph.initial];
  while (queue.length) {
    const n = byId.get(queue.shift());
    for (const dir of DIRS) {
      const t = n[dir];
      if (t !== null && !seen.has(t)) { seen.add(t); queue.push(t); }
    }
  }
  for (const n of graph.nodes) {
    if (!seen.has(n.id)) {
      warnings.push(`focus: "${n.name}" is unreachable from the initial focus by D-pad`);
    }
  }
  return warnings;
}
