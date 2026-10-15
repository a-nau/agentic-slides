"""Tests for baking SVG <marker> arrowheads into explicit geometry.

PowerPoint's SVG renderer drops <marker> elements, so arrowheads must become
real shapes positioned/rotated at each path's end.
"""

import xml.etree.ElementTree as ET

from scripts.pptx_export import svg_arrows

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
    '<defs><marker id="m" markerWidth="11" markerHeight="11" refX="8" refY="4" '
    'orient="auto"><path d="M0,0 L9,4 L0,8 z" fill="#3b82f6"/></marker></defs>'
    '<path d="M0,0 L100,0" fill="none" stroke="#666" stroke-width="2" '
    'marker-end="url(#m)"/>'
    "</svg>"
)


def test_marker_reference_removed():
    out = svg_arrows.bake_markers(SVG)
    assert "marker-end" not in out


def test_baked_triangle_matches_line_colour_and_has_transform():
    out = svg_arrows.bake_markers(SVG)
    # arrowhead takes the LINE's stroke (#666), not the marker's own fill,
    # so a head never mismatches its line
    assert 'fill="#666"' in out
    assert "matrix(" in out          # placed via explicit matrix transform


def test_baked_arrow_at_correct_end_point_and_angle():
    # horizontal line ending at (100,0), angle 0, stroke-width 2, refX/Y 8/4:
    # matrix = (2,0,0,2, 100-2*8, 0-2*4) = (2,0,0,2,84,-8)
    out = svg_arrows.bake_markers(SVG)
    root = ET.fromstring(out)
    ns = "{http://www.w3.org/2000/svg}"
    g = next(e for e in root.iter(ns + "g") if e.get("transform", "").startswith("matrix"))
    nums = [float(x) for x in g.get("transform")[7:-1].split(",")]
    assert nums[0] == 84 or abs(nums[4] - 84) < 0.5  # e ~ 84
    assert abs(nums[5] - (-8)) < 0.5                  # f ~ -8


def test_no_markers_passthrough():
    plain = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    assert svg_arrows.bake_markers(plain) == plain
