"""Pure CSS-px → OOXML conversion helpers.

Browser geometry comes back in CSS pixels (96 px/inch). PowerPoint measures
length in EMU (914400 EMU/inch) and font size in points (72 pt/inch).
"""

import re

from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

EMU_PER_PX = 9525  # 914400 / 96
PT_PER_PX = 0.75   # 72 / 96

_RGB_RE = re.compile(
    r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", re.IGNORECASE
)
_HEX_RE = re.compile(r"#?([0-9a-fA-F]{6})$")
_ALPHA_RE = re.compile(
    r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)", re.IGNORECASE
)

_ALIGN = {
    "left": PP_ALIGN.LEFT,
    "start": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "end": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}

_ANCHOR = {
    "top": MSO_ANCHOR.TOP,
    "middle": MSO_ANCHOR.MIDDLE,
    "bottom": MSO_ANCHOR.BOTTOM,
}


def px_to_emu(px: float) -> int:
    """CSS pixels to EMU, rounded to the nearest EMU."""
    return round(px * EMU_PER_PX)


def px_to_pt(px: float) -> float:
    """CSS pixels to points."""
    return px * PT_PER_PX


def parse_color(css: str) -> str | None:
    """A CSS color string to an upper-case ``RRGGBB`` hex string.

    Handles ``rgb()``/``rgba()`` (the form getComputedStyle returns) and
    ``#rrggbb``. Returns ``None`` for anything else (e.g. ``transparent``).
    """
    if css is None:
        return None
    m = _RGB_RE.match(css.strip())
    if m:
        return "{:02X}{:02X}{:02X}".format(*(int(g) for g in m.groups()))
    m = _HEX_RE.match(css.strip())
    if m:
        return m.group(1).upper()
    return None


def parse_alpha(css: str) -> float:
    """Alpha (0..1) of an ``rgba()`` colour; 1.0 for ``rgb()``/anything else."""
    if css is None:
        return 1.0
    m = _ALPHA_RE.match(css.strip())
    return float(m.group(1)) if m else 1.0


def map_align(css_text_align: str) -> PP_ALIGN:
    """CSS ``text-align`` to a PowerPoint paragraph alignment."""
    return _ALIGN.get((css_text_align or "").strip().lower(), PP_ALIGN.LEFT)


def map_anchor(vertical: str) -> MSO_ANCHOR:
    """A simple top/middle/bottom string to a text-frame vertical anchor."""
    return _ANCHOR.get((vertical or "").strip().lower(), MSO_ANCHOR.TOP)
