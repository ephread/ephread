"""Builds the profile header: one SVG per theme and availability, with text outlined.

    pip install fonttools brotli uharfbuzz
    python tools/header/build.py ../ephread.github.io/node_modules/@fontsource-variable media
"""

import io
import re
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).parent
FONTS = Path(sys.argv[1])  # node_modules/@fontsource-variable
OUT = Path(sys.argv[2])

W, H = 1000, 360
# Transparent space under the card, so the README's text doesn't sit right against it.
MARGIN = 32

THEMES = {
    "light": dict(bg="#f9f5f1", surface="#fff", line="#e6e0d8", fg="#2e3036", muted="#555861"),
    "dark": dict(bg="#181715", surface="#23211e", line="#38342f", fg="#f2ede7", muted="#b3aca3"),
}

STATUSES = {
    "available": ("Open to work", "#2f9e0b"),
    "limited": ("Limited availability", "#e8640f"),
    "unavailable": ("Unavailable for new projects", "#d4472c"),
}


def load(path, variations):
    tt = TTFont(path)
    buf = io.BytesIO()
    tt.flavor = None
    tt.save(buf)
    face = hb.Face(buf.getvalue())
    font = hb.Font(face)
    font.set_variations(variations)
    return font, face.upem


BRICOLAGE = load(FONTS / "bricolage-grotesque/files/bricolage-grotesque-latin-opsz-normal.woff2",
                 {"opsz": 80, "wght": 700})
INTER = {w: load(FONTS / "inter/files/inter-latin-wght-normal.woff2", {"wght": w}) for w in (400, 500, 600)}


def text(s, font, size, x, y, tracking=0.0):
    """Outlines `s` with its baseline at (x, y). Returns (path data, advance width)."""
    hbfont, upem = font
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    scale = size / upem
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    cursor = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        t = (scale, 0, 0, -scale, x + (cursor + pos.x_offset) * scale, y - pos.y_offset * scale)
        hbfont.draw_glyph_with_pen(info.codepoint, TransformPen(pen, t))
        cursor += pos.x_advance + tracking * upem
    return pen.getCommands(), (cursor - tracking * upem) * scale


def svg(theme, status):
    c = THEMES[theme]
    label, dot = STATUSES[status]
    parts = []

    # Availability pill, as in the site's hero.
    px, py, ph = 56, 56, 40
    d, tw = text(label, INTER[500], 17, px + 34, py + 26)
    pw = 34 + tw + 18
    parts.append(f'<rect x="{px}" y="{py}" width="{pw:.1f}" height="{ph}" rx="20" fill="{c["surface"]}" stroke="{c["line"]}"/>')
    parts.append(f'<circle cx="{px + 20}" cy="{py + 20}" r="5" fill="{dot}"/>')
    parts.append(f'<path fill="{c["fg"]}" d="{d}"/>')

    # Headline and intro.
    d, _ = text("Hey, I’m Fred.", BRICOLAGE, 84, 52, 200, tracking=-0.02)
    parts.append(f'<path fill="{c["fg"]}" d="{d}"/>')
    d, _ = text("Independent iOS & watchOS developer.", INTER[400], 26, 56, 258)
    parts.append(f'<path fill="{c["muted"]}" d="{d}"/>')
    d1, w1 = text("I grow ", INTER[400], 26, 56, 298)
    apple_size = 26 * 1.1
    ax = 56 + w1
    d2, _ = text(" in my backyard.", INTER[400], 26, ax + apple_size, 298)
    parts.append(f'<path fill="{c["muted"]}" d="{d1}{d2}"/>')
    apple = (HERE / "apple.svg").read_text()
    apple_inner = re.search(r"<svg[^>]*>(.*)</svg>", apple, re.S).group(1)
    s = apple_size / 50
    parts.append(f'<g transform="translate({ax:.1f} {298 + 0.2 * 26 - apple_size * 43 / 50:.1f}) scale({s:.4f})">{apple_inner}</g>')

    title = f"Hey, I’m Fred. Independent iOS &amp; watchOS developer. I grow apples in my backyard. {label}."
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + MARGIN}" viewBox="0 0 {W} {H + MARGIN}" role="img">'
        f"<title>{title}</title>"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="32" fill="{c["bg"]}" stroke="{c["line"]}"/>'
        + "".join(parts) + "</svg>\n"
    )


OUT.mkdir(parents=True, exist_ok=True)
for theme in THEMES:
    for status in STATUSES:
        (OUT / f"header-{status}-{theme}.svg").write_text(svg(theme, status))
