"""Bake SVG ``<marker>`` arrowheads into explicit geometry.

PowerPoint's SVG renderer ignores ``<marker>`` elements, so any ``marker-end`` /
``marker-start`` arrowhead simply vanishes (the line stays). This rewrites each
marker reference into a real shape (a copy of the marker's content) positioned,
rotated and scaled at the path's end/start vertex, then drops the reference so
renderers that *do* support markers don't draw it twice.

Handles the marker form these decks use: no ``viewBox``, default
``markerUnits="strokeWidth"``, ``orient="auto"``, ``refX``/``refY`` in content
coordinates.
"""

import copy
import math
import re

from lxml import etree
from svgpathtools import parse_path

_SVG = "http://www.w3.org/2000/svg"
_URL_RE = re.compile(r"url\(#(.+?)\)")


def _q(tag):
    return f"{{{_SVG}}}{tag}"


def bake_markers(svg_str: str) -> str:
    root = etree.fromstring(svg_str.encode("utf-8"))
    markers = {m.get("id"): m for m in root.iter(_q("marker")) if m.get("id")}
    if not markers:
        return svg_str

    todo = []  # (element, marker, end_point_t)
    for el in root.iter():
        d = el.get("d")
        if not d:
            continue
        for attr, t in (("marker-start", 0.0), ("marker-end", 1.0)):
            ref = el.get(attr)
            if not ref:
                continue
            m = _URL_RE.match(ref.strip())
            mk = markers.get(m.group(1)) if m else None
            if mk is not None:
                todo.append((el, mk, t, attr))

    changed = False
    for el, mk, t, attr in todo:
        g = _bake(el, mk, t)
        del el.attrib[attr]
        if g is not None:
            el.addnext(g)  # sibling, same transform context, drawn on top
            changed = True

    return etree.tostring(root).decode() if changed else svg_str


def _bake(el, mk, t):
    try:
        path = parse_path(el.get("d"))
        pt = path.point(t)
        tan = path.unit_tangent(t)
    except Exception:
        return None
    px, py = pt.real, pt.imag
    ang = math.atan2(tan.imag, tan.real)
    sw = float(el.get("stroke-width", 1) or 1)
    rx = float(mk.get("refX", 0) or 0)
    ry = float(mk.get("refY", 0) or 0)

    # matrix = translate(P) · rotate(ang) · scale(sw) · translate(-refX,-refY)
    cos, sin = math.cos(ang), math.sin(ang)
    a, b, c, d = sw * cos, sw * sin, -sw * sin, sw * cos
    e = px - sw * (rx * cos - ry * sin)
    f = py - sw * (rx * sin + ry * cos)

    g = etree.Element(_q("g"))
    g.set("transform", f"matrix({a:.4f},{b:.4f},{c:.4f},{d:.4f},{e:.4f},{f:.4f})")
    # Colour the head to match the line. Decks sometimes reuse a marker of one
    # colour on a line of another (e.g. a blue arrowhead on a purple line); the
    # arrowhead matching its own line is what reads as correct.
    stroke = el.get("stroke")
    for child in mk:
        cc = copy.deepcopy(child)
        if stroke and stroke != "none":
            cc.set("fill", stroke)
        elif cc.get("fill") in (None, "context-stroke", "context-fill"):
            cc.set("fill", "#000")
        g.append(cc)
    return g
