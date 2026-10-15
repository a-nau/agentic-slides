"""Tests for pure CSS-px → OOXML conversion helpers."""

import pytest
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from scripts.pptx_export import convert


class TestPxToEmu:
    def test_one_css_px_is_9525_emu(self):
        assert convert.px_to_emu(1) == 9525

    def test_rounds_to_nearest_emu(self):
        # 100.4 px * 9525 = 956310.0 -> 956310
        assert convert.px_to_emu(100.4) == 956310

    def test_full_slide_width_1280px_is_standard_16x9(self):
        # 1280 px -> 13.333.. inches -> 12192000 EMU (PowerPoint's 16:9 width)
        assert convert.px_to_emu(1280) == 12192000

    def test_full_slide_height_720px(self):
        assert convert.px_to_emu(720) == 6858000


class TestPxToPt:
    def test_16px_is_12pt(self):
        assert convert.px_to_pt(16) == pytest.approx(12.0)

    def test_fractional(self):
        assert convert.px_to_pt(51.2) == pytest.approx(38.4)


class TestParseColor:
    def test_rgb_form(self):
        assert convert.parse_color("rgb(59, 130, 246)") == "3B82F6"

    def test_rgba_drops_alpha(self):
        assert convert.parse_color("rgba(59,130,246, 0.5)") == "3B82F6"

    def test_hex_passthrough(self):
        assert convert.parse_color("#3b82f6") == "3B82F6"

    def test_white(self):
        assert convert.parse_color("rgb(255, 255, 255)") == "FFFFFF"

    def test_unparseable_returns_none(self):
        assert convert.parse_color("transparent") is None


class TestMapAlign:
    def test_left(self):
        assert convert.map_align("left") == PP_ALIGN.LEFT

    def test_center(self):
        assert convert.map_align("center") == PP_ALIGN.CENTER

    def test_right(self):
        assert convert.map_align("right") == PP_ALIGN.RIGHT

    def test_justify(self):
        assert convert.map_align("justify") == PP_ALIGN.JUSTIFY

    def test_start_is_left(self):
        assert convert.map_align("start") == PP_ALIGN.LEFT

    def test_unknown_defaults_left(self):
        assert convert.map_align("whatever") == PP_ALIGN.LEFT


class TestMapAnchor:
    def test_top(self):
        assert convert.map_anchor("top") == MSO_ANCHOR.TOP

    def test_middle(self):
        assert convert.map_anchor("middle") == MSO_ANCHOR.MIDDLE

    def test_bottom(self):
        assert convert.map_anchor("bottom") == MSO_ANCHOR.BOTTOM
