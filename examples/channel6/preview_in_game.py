#!/usr/bin/env python3
"""Composite the browser over a game frame, the way it actually ships.

    PYTHONPATH=packages/baker python3 preview_in_game.py <ui.uib> <out.png>

Every other preview in this example renders the blob over flat navy,
which is the right ground truth for bring-up but hides the whole point of
the design: this UI is an *overlay*. The root is a translucent scrim, the
blob carries no background of its own beyond that, and `ps2ui_render()`
draws straight into whatever is already in the framebuffer. If your app
skips the `gsKit_clear()` the sample ELF does, the game stays visible
underneath.

So this renders the blob onto full transparency and composites it over a
frame, which is exactly the operation the GS performs. The frame is drawn
here from flat shapes rather than captured: shipping a real game's
pixels into a repository is a licensing problem, and a synthetic frame
makes a better test anyway because the bright horizon band lands right
where the cover grid does, which is where a scrim that is too thin shows
up first.
"""

import sys

from PIL import Image, ImageDraw

from ps2ui_bake import preview
from ps2ui_bake.uib import read_uib

HORIZON = 186


def game_frame(w: int, h: int) -> Image.Image:
    """A driving-game frame: dusk sky, hills, a road to the vanishing
    point, and a corner of HUD. Bright where the UI is darkest."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)

    # Sky: deep blue up top warming to amber at the horizon.
    top, bottom = (26, 34, 78), (232, 146, 74)
    for y in range(HORIZON):
        t = y / HORIZON
        d.line([(0, y), (w, y)],
               fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    d.ellipse([w // 2 - 46, HORIZON - 62, w // 2 + 46, HORIZON + 30],
              fill=(255, 214, 138, 255))

    # Two hill ranges, the near one darker.
    for depth, (color, amp, base) in enumerate((
            ((92, 74, 116, 255), 26, HORIZON - 14),
            ((44, 38, 66, 255), 16, HORIZON - 4))):
        pts = [(0, h)]
        for x in range(0, w + 40, 40):
            pts.append((x, base - (amp if (x // 40 + depth) % 2 else amp // 3)))
        pts.append((w, h))
        d.polygon(pts, fill=color)

    # Ground and a road converging on the vanishing point.
    d.rectangle([0, HORIZON, w, h], fill=(38, 44, 40, 255))
    vp = (w // 2, HORIZON)
    d.polygon([vp, (w // 2 - 300, h), (w // 2 + 300, h)], fill=(58, 58, 62, 255))
    d.polygon([vp, (w // 2 - 316, h), (w // 2 - 292, h)], fill=(226, 226, 214, 255))
    d.polygon([vp, (w // 2 + 292, h), (w // 2 + 316, h)], fill=(226, 226, 214, 255))

    # Centre dashes, crowding toward the horizon. Placed by fraction of
    # the road's depth rather than by a shrinking step: a geometric step
    # converges short of the horizon and loops forever.
    depth = h - HORIZON
    for i in range(14):
        t = (i / 14.0) ** 2.2          # dense near the vanishing point
        y0 = h - t * depth
        y1 = max(HORIZON + 3, y0 - max(3.0, 26 * (1 - t)))
        near = (y0 - HORIZON) / depth
        half = max(1, round(5 * near))
        inner = max(1, half - 1)
        d.polygon([(vp[0] - half, y0), (vp[0] + half, y0),
                   (vp[0] + inner, y1), (vp[0] - inner, y1)],
                  fill=(226, 226, 214, 255))

    # A corner of HUD, so the frame reads as a game and not a wallpaper.
    d.rectangle([w - 148, h - 54, w - 24, h - 22], fill=(0, 0, 0, 120))
    d.rectangle([w - 144, h - 30, w - 28, h - 26], fill=(120, 220, 190, 255))
    d.rectangle([w - 144, h - 30, w - 74, h - 26], fill=(255, 232, 120, 255))
    return img


def main(uib_path: str, out_path: str) -> int:
    uib = read_uib(uib_path)
    frame = game_frame(uib.canvas_w, uib.canvas_h)
    # Transparent ground: what ps2ui_render() draws, and nothing else.
    ui = preview.render(uib, background=(0, 0, 0, 0), screen="games")
    frame.alpha_composite(ui)
    frame.save(out_path)
    print(f"ps2ui-bake: in-game composite -> {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <ui.uib> <out.png>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
