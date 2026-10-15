#!/usr/bin/env python3
"""Generate the gallery's figures (images/*.svg).

    python3 make_figures.py && python3 build_deck.py

Rules every figure follows (see the slide-deck skill's animating-figures.md):
- CSS keyframes only (multi-phase SMIL breaks inside Marp's foreignObject).
- Every class and keyframe name carries a per-figure prefix: all slides share
  one HTML document.
- The static frame (plain attributes) is the complete picture; animations only
  move, fade, or draw things in. PDF/PPTX exports show the static frame.
- Hover text lives in data-tiphead / data-tip (no double quotes inside); the
  deck's hover toolkit shows it.

Data: data/datasets.csv (public dataset facts from the datasets' papers) and
data/land.json (Natural Earth 1:110m, public domain).
"""
import csv
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"

BG, CARD, BORDER = "#111111", "#1a1a1a", "#2a2a2a"
ACCENT, LIGHT, GREEN, ORANGE, PURPLE, RED, YELLOW = (
    "#3b82f6", "#93c5fd", "#3fb950", "#f0883e", "#bc8cff", "#f85149", "#e3b341")
TEXT, SUB, MUTED = "#f0f0f0", "#a0a0a0", "#666666"
FAM = {"perception": ACCENT, "prediction": ORANGE, "planning": PURPLE,
       "e2e": GREEN, "simulation": YELLOW}
FAM_LABEL = {"perception": "perception", "prediction": "prediction", "planning": "planning",
             "e2e": "multitask", "simulation": "reconstruction"}
ROOT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 600" font-family="Inter, sans-serif">'
BASE = (f".t{{fill:{TEXT};font-weight:700}}.d{{fill:{SUB}}}.mu{{fill:{MUTED}}}"
        f".m{{font-family:'JetBrains Mono',monospace;fill:{LIGHT}}}")


def esc(s):
    return str(s).replace("&", "&amp;").replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")


def tip(head, body):
    return f'data-tiphead="{esc(head)}" data-tip="{esc(body)}"'


def write(name, css, body):
    svg = ROOT + f"\n<style>{BASE}{css}</style>\n" + body.strip() + "\n</svg>"
    svg = "\n".join(l for l in svg.split("\n") if l.strip())  # no blank lines (markdown)
    (OUT / f"{name}.svg").write_text(svg + "\n")
    print("wrote", f"images/{name}.svg")


def datasets():
    with open(HERE / "data/datasets.csv") as f:
        return list(csv.DictReader(f))


def fmt(n):
    return f"{float(n):,.0f}" if float(n) >= 10 else n


def ds_tip(r):
    bits = [f"{r['org']}, {r['year']}", r["locations"]]
    if r["hours"]:
        bits.append(f"{r['hours']} h recorded")
    if r["scenes"]:
        bits.append(f"{fmt(r['scenes'])} scenes")
    if r["images"]:
        bits.append(f"{fmt(r['images'])} images")
    bits.append(f"use: {r['primary_use']} · license: {r['license']}")
    return tip(r["dataset"], " · ".join(bits))


def short_places(s, n=34):
    """Fit a location list into n characters: drop trailing places, count them."""
    parts = s.split(", ")
    k = len(parts)
    while k > 1 and len(", ".join(parts[:k]) + f" +{len(parts) - k}") > n:
        k -= 1
    return s if len(s) <= n else ", ".join(parts[:k]) + f" +{len(parts) - k}"


# ── map: where public driving datasets were recorded (hover + linked highlight) ──
CITY = {
    "sf": (37.77, -122.42), "mtv": (37.39, -122.08), "palo": (37.44, -122.14),
    "bayarea": (37.87, -122.27), "phoenix": (33.45, -112.07), "vegas": (36.17, -115.14),
    "ny": (40.71, -74.0), "boston": (42.36, -71.06), "pitt": (40.44, -79.99),
    "miami": (25.76, -80.19), "detroit": (42.33, -83.05), "dc": (38.9, -77.04),
    "austin": (30.27, -97.74), "karlsruhe": (49.0, 8.4), "munich": (48.14, 11.58),
    "ingolstadt": (48.76, 11.43), "london": (51.51, -0.13), "singapore": (1.35, 103.82),
}
REGION = {"germany": (51.0, 10.0, 16), "europe": (50.0, 14.0, 34), "china": (34.0, 108.0, 30)}


def fig_map():
    LON0, LON1, LAT0, LAT1 = -128, 128, -4, 62
    X0, X1, Y0 = 30, 1130, 20
    SX = (X1 - X0) / (LON1 - LON0)
    SY = SX * 1.2
    proj = lambda lat, lon: (X0 + (lon - LON0) * SX, Y0 + (LAT1 - lat) * SY)
    land = json.loads((HERE / "data/land.json").read_text())["rings"]
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    paths = []
    for ring in land:
        pts = [proj(la, lo) for lo, la in ring]  # the clip path trims the edges
        if len(pts) < 3:
            continue
        paths.append("M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in pts) + "Z")
    YB = proj(LAT0, 0)[1]
    body += (f'<defs><clipPath id="mp-clip"><rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{YB - Y0:.0f}" rx="12"/></clipPath></defs>'
             f'<rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{YB - Y0:.0f}" rx="12" fill="#0d1117"/>'
             f'<path clip-path="url(#mp-clip)" d="{"".join(paths)}" fill="#1c222b" stroke="#2c3440" stroke-width="0.8"/>'
             f'<rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{YB - Y0:.0f}" rx="12" fill="none" stroke="{BORDER}"/>')
    css = (".mp-ds{cursor:help}.mp-ds:hover .mp-pt{stroke:#fff;stroke-width:2.5}"
           ".mp-ds:hover .mp-row rect{fill:#1d2633}")
    rows = datasets()
    used = {}
    for i, r in enumerate(rows):
        col = FAM[r["family"]]
        g = f'<g class="mp-ds" {ds_tip(r)}>'
        for key in r["points"].split():
            if key in REGION:
                la, lo, rad = REGION[key]
                x, y = proj(la, lo)
                g += (f'<circle class="mp-pt" cx="{x:.0f}" cy="{y:.0f}" r="{rad}" fill="{col}" fill-opacity=".12" '
                      f'stroke="{col}" stroke-width="1.5" stroke-dasharray="4 4"/>')
                continue
            la, lo = CITY[key]
            x, y = proj(la, lo)
            k = used.get(key, 0)
            used[key] = k + 1
            if k:  # several datasets in one city: fan them around it
                a = k * 2.1
                x, y = x + 9 * math.cos(a), y + 9 * math.sin(a)
            g += f'<circle class="mp-pt" cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{col}" stroke="{BG}" stroke-width="1.5"/>'
        lx, ry = 30 + (i // 5) * 370, 405 + (i % 5) * 27  # list entry: hovering it highlights the points
        g += (f'<g class="mp-row"><rect x="{lx}" y="{ry - 19}" width="350" height="25" rx="6" fill="{BG}"/>'
              f'<circle cx="{lx + 14}" cy="{ry - 6}" r="6" fill="{col}"/>'
              f'<text x="{lx + 30}" y="{ry}" class="t" font-size="16">{esc(r["dataset"])}</text>'
              f'<text x="{lx + 340}" y="{ry}" text-anchor="end" class="mu" font-size="14">{esc(short_places(r["locations"]))}</text></g>')
        g += "</g>"
        body += g
    body += f'<text x="30" y="562" class="mu" font-size="15">colour = task:</text>'
    lx = 140
    for fam, col in FAM.items():
        body += (f'<circle cx="{lx + 6}" cy="{557}" r="6" fill="{col}"/>'
                 f'<text x="{lx + 18}" y="562" class="d" font-size="15">{FAM_LABEL[fam]}</text>')
        lx += 145
    body += (f'<text x="30" y="592" class="mu" font-size="13">Dashed circle: recorded across a whole country or region '
             f'(Cityscapes, ONCE, ZOD), not in named cities. Hover a point or a name. Map: Natural Earth.</text>')
    write("map", css, body)


# ── timeline: cards in stacked lanes above and below a year axis ────────────
def fig_timeline():
    X0, X1, AY = 50, 1110, 280
    Y0, Y1 = 2012, 2025  # band edges: each year owns one band of the axis
    xr = lambda yr: X0 + (yr - Y0) / (Y1 - Y0) * (X1 - X0)
    css = ".tl-c{cursor:help}.tl-c:hover rect{fill:#1d2633;stroke-width:2.5}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += f'<line x1="{X0}" y1="{AY}" x2="{X1}" y2="{AY}" stroke="{MUTED}" stroke-width="2"/>'
    for yr in range(Y0, Y1 + 1):
        body += f'<line x1="{xr(yr):.0f}" y1="{AY - 6}" x2="{xr(yr):.0f}" y2="{AY + 6}" stroke="{SUB}" stroke-width="2"/>'
        if yr < Y1:
            body += (f'<text x="{xr(yr + 0.5):.0f}" y="{AY + 27}" text-anchor="middle" class="d" '
                     f'font-size="14" font-weight="700">{yr}</text>')
    rows = sorted(datasets(), key=lambda r: (int(r["year"]), r["dataset"]))
    per_year = {}
    for r in rows:
        per_year.setdefault(int(r["year"]), []).append(r)
    LANE, H = 50, 40
    items = []  # (row, dot x, card width)
    for yr, group in per_year.items():
        for k, r in enumerate(group):  # spread a year's datasets evenly across its band
            sub = f"{yr} · {r['primary_use']}"
            items.append((r, sub, xr(yr + (k + 0.5) / len(group)), max(len(r["dataset"]) * 9.4, len(sub) * 7.0) + 24))

    def fits(placed, side, lane, x0, x1, lx):
        for s_, l_, a, b, ox in placed:
            if s_ != side:
                continue
            if l_ == lane and not (x1 + 8 < a or x0 - 8 > b):
                return False  # overlaps a card in the same lane
            if l_ < lane and a - 3 < lx < b + 3:
                return False  # our leader would cross a nearer card
            if l_ > lane and x0 - 3 < ox < x1 + 3:
                return False  # we would cover a farther card's leader
        return True

    best = [None, 1e9, 0]  # layout, its cost, nodes visited

    def solve(placed, cost):  # branch and bound (with a node budget): fewest stacked lanes
        best[2] += 1
        if cost >= best[1] or best[2] > 300000:
            return
        if len(placed) == len(items):
            best[:2] = [placed, cost]
            return
        _, _, x, w = items[len(placed)]
        pref = -1 if len(placed) % 2 == 0 else 1
        for lane in range(4):
            for side in (pref, -pref):
                for bx in (x - w / 2, x - 12, x - w + 12):
                    bx = min(max(bx, 8), 1152 - w)
                    if fits(placed, side, lane, bx, bx + w, x):
                        solve(placed + [(side, lane, bx, bx + w, x)], cost + lane * lane)

    solve([], 0)
    leaders, cards, dots = "", "", ""
    for (r, sub, x, w), (side, lane, bx, _, _) in zip(items, best[0]):
        by = AY - 76 - lane * LANE - H if side < 0 else AY + 44 + lane * LANE
        ly = by + H if side < 0 else by
        col = FAM[r["family"]]
        leaders += f'<line x1="{x:.0f}" y1="{AY}" x2="{x:.0f}" y2="{ly:.0f}" stroke="{col}" stroke-width="1.2" stroke-dasharray="2 3"/>'
        cards += (f'<g class="tl-c" {ds_tip(r)}><rect x="{bx:.0f}" y="{by:.0f}" width="{w:.0f}" height="{H}" rx="7" fill="{CARD}" stroke="{col}" stroke-width="1.5"/>'
                  f'<text x="{bx + 12:.0f}" y="{by + 18:.0f}" font-size="15" font-weight="700" fill="{col}" '
                  f'font-family="JetBrains Mono, monospace">{esc(r["dataset"])}</text>'
                  f'<text x="{bx + 12:.0f}" y="{by + 33:.0f}" class="d" font-size="12">{esc(sub)}</text></g>')
        dots += f'<circle cx="{x:.0f}" cy="{AY}" r="6" fill="{col}" stroke="{BG}" stroke-width="1.5"/>'
    body += leaders + cards
    body += dots  # dots last, so they sit on top of the leaders
    lx, ly = 50, 556
    body += f'<rect x="{lx - 16}" y="{ly - 22}" width="1092" height="40" rx="8" fill="{CARD}" stroke="{BORDER}"/>'
    for fam, col in FAM.items():
        body += (f'<circle cx="{lx + 6}" cy="{ly - 2}" r="6" fill="{col}"/>'
                 f'<text x="{lx + 18}" y="{ly + 3}" fill="{TEXT}" font-size="14">{FAM_LABEL[fam]}</text>')
        lx += 140
    body += (f'<text x="1110" y="{ly + 3}" text-anchor="end" class="mu" font-size="13">'
             f'Within a year, datasets are spaced in alphabetical order.</text>')
    write("timeline", css, body)


# ── hours: recorded hours per dataset on a log scale, hover for details ─────
def fig_hours():
    X0, X1, YB, YT = 130, 1110, 520, 60
    Y0, Y1 = 2011.5, 2024.5
    L0, L1 = -1, 3.5  # log10 hours
    xr = lambda yr: X0 + (yr - Y0) / (Y1 - Y0) * (X1 - X0)
    yr_ = lambda h: YB - (math.log10(h) - L0) / (L1 - L0) * (YB - YT)
    css = ".bb-b{cursor:help}.bb-b:hover circle{stroke:#fff;stroke-width:2.5}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    for h, lab in ((0.1, "6 min"), (1, "1 h"), (10, "10 h"), (100, "100 h"), (1000, "1,000 h")):
        y = yr_(h)
        body += (f'<line x1="{X0}" y1="{y:.0f}" x2="{X1}" y2="{y:.0f}" stroke="{BORDER}" stroke-dasharray="3 6"/>'
                 f'<text x="{X0 - 14}" y="{y + 5:.0f}" text-anchor="end" class="mu" font-size="14">{lab}</text>')
    for yr in range(2012, 2025, 2):
        body += f'<text x="{xr(yr):.0f}" y="{YB + 30}" text-anchor="middle" class="mu" font-size="14">{yr}</text>'
    body += f'<line x1="{X0}" y1="{YB}" x2="{X1}" y2="{YB}" stroke="{MUTED}" stroke-width="2"/>'
    body += f'<text x="{X0}" y="{YT - 22}" class="d" font-size="15">recorded driving (log scale)</text>'
    rows = [r for r in datasets() if r["hours"]]
    rows.sort(key=lambda r: int(r["year"]))
    nudge = {"nuScenes": 16, "Waymo Open": -16}  # same year, similar hours
    left = {"BDD100K", "Waymo Open", "Lyft Level 5"}  # label on the left of the bubble
    for r in rows:
        h = float(r["hours"])
        yr = int(r["year"])
        x = xr(yr) + nudge.get(r["dataset"], 0)
        y = yr_(h)
        col = FAM[r["family"]]
        anchor, dx = ("end", -22) if r["dataset"] in left or x > 960 else ("start", 22)
        body += (f'<g class="bb-b" {ds_tip(r)}><circle cx="{x:.0f}" cy="{y:.0f}" r="15" fill="{col}" fill-opacity=".85" stroke="{BG}" stroke-width="2"/>'
                 f'<text x="{x + dx:.0f}" y="{y + 5:.0f}" text-anchor="{anchor}" class="t" font-size="15">{esc(r["dataset"])}</text></g>')
    missing = sorted(r["dataset"] for r in datasets() if not r["hours"])
    body += (f'<text x="30" y="572" class="mu" font-size="13">Hours as each paper reports them: some count all logged driving '
             f'(Lyft, nuPlan), others only the annotated clips (nuScenes, Waymo Open). Compare orders of magnitude.</text>'
             f'<text x="30" y="592" class="mu" font-size="13">{len(rows)} of {len(datasets())} datasets shown: '
             f'{", ".join(missing)} report images, not hours.</text>')
    write("hours", css, body)


# ── diffusion: noise particles flow onto the data distribution ────────────────
def fig_diffusion():
    T = 9
    rnd = random.Random(7)
    css = (f".df-p{{animation:df-p {T}s cubic-bezier(.5,0,.3,1) infinite}}"
           f".df-bar{{transform-box:fill-box;transform-origin:left;animation:df-bar {T}s linear infinite}}"
           f".df-c1{{animation:df-c1 {T}s infinite}}.df-c2{{animation:df-c2 {T}s infinite}}.df-c3{{animation:df-c3 {T}s infinite}}"
           f"@keyframes df-bar{{0%,10%{{transform:scaleX(1)}}70%,100%{{transform:scaleX(0)}}}}"
           f"@keyframes df-c1{{0%,12%{{opacity:1}}16%,100%{{opacity:.25}}}}"
           f"@keyframes df-c2{{0%,14%{{opacity:.25}}18%,66%{{opacity:1}}70%,100%{{opacity:.25}}}}"
           f"@keyframes df-c3{{0%,68%{{opacity:.25}}72%,96%{{opacity:1}}100%{{opacity:.25}}}}")
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    cx0, cy0, W, H = 300, 60, 560, 400  # the 2-D plane
    body += f'<rect x="{cx0}" y="{cy0}" width="{W}" height="{H}" rx="16" fill="#0d1117" stroke="{BORDER}"/>'
    # data: a two-moons distribution; faint guide of where the data lives
    def moon(t, up):
        a = math.pi * t
        return (math.cos(a), math.sin(a)) if up else (1 - math.cos(a), 0.5 - math.sin(a))
    to_px = lambda u, v: (cx0 + W / 2 + (u - 0.5) * 150, cy0 + H / 2 - (v - 0.25) * 150)
    guide = []
    for up in (True, False):
        pts = [to_px(*moon(t / 40, up)) for t in range(41)]
        guide.append("M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts))
    body += f'<path d="{" ".join(guide)}" fill="none" stroke="{GREEN}" stroke-width="26" stroke-linecap="round" opacity=".08"/>'
    for i in range(110):
        up = i % 2 == 0
        u, v = moon(rnd.random(), up)
        x, y = to_px(u + rnd.gauss(0, 0.06), v + rnd.gauss(0, 0.06))
        nx = cx0 + 30 + rnd.random() * (W - 60)  # start: pure noise
        ny = cy0 + 30 + rnd.random() * (H - 60)
        mx, my = (nx + x) / 2 + rnd.gauss(0, 22), (ny + y) / 2 + rnd.gauss(0, 22)  # a noisy midway step
        k = f"df-k{i}"
        css += (f".{k}{{animation-name:{k}}}"
                f"@keyframes {k}{{0%,10%{{transform:translate({nx - x:.0f}px,{ny - y:.0f}px);opacity:.9}}"
                f"40%{{transform:translate({mx - x:.0f}px,{my - y:.0f}px)}}70%,92%{{transform:none;opacity:1}}"
                f"100%{{transform:translate({nx - x:.0f}px,{ny - y:.0f}px);opacity:0}}}}")
        body += f'<circle class="df-p {k}" cx="{x:.0f}" cy="{y:.0f}" r="4.5" fill="{GREEN if up else ACCENT}"/>'
    # left: noise level; right: phase captions
    body += (f'<text x="60" y="110" class="d" font-size="15">noise level</text>'
             f'<rect x="60" y="124" width="200" height="14" rx="7" fill="{BORDER}"/>'
             f'<rect class="df-bar" x="60" y="124" width="200" height="14" rx="7" fill="{ORANGE}"/>'
             f'<text x="60" y="166" class="mu" font-size="14">t = 1 (pure noise) → t = 0 (data)</text>')
    for j, (c, head, subs) in enumerate((("df-c1", "1 · sample noise", ["x ~ N(0, I)"]),
                                         ("df-c2", "2 · denoise step by step", ["x ← x + ε·score(x, t)", "+ √(2ε)·z"]),
                                         ("df-c3", "3 · land on the data", ["samples trace the moons"]))):
        y = 230 + j * 90
        body += f'<g class="{c}"><text x="890" y="{y}" class="t" font-size="19">{head}</text>'
        for k, sub in enumerate(subs):
            body += f'<text x="{890 + 24 * (k > 0)}" y="{y + 26 + k * 20}" class="m" font-size="14">{esc(sub)}</text>'
        body += "</g>"
    for k, line in enumerate(("score(x, t): a trained network's estimate of the direction in which data gets more likely,",
                              "at noise level t. z: fresh Gaussian noise each step, so samples spread over the data, not one point.",
                              "Data: two moons, a toy 2-D dataset of two interleaved crescents. Positions are synthetic.")):
        body += f'<text x="{cx0}" y="{cy0 + H + 36 + k * 22}" class="mu" font-size="14">{esc(line)}</text>'
    write("diffusion", css, body)


# ── attention: one query attends over the sentence, weights grow, output mixes ─
def fig_attention():
    T = 10
    toks = ["The", "cat", "sat", "on", "the", "mat", "because", "it", "was", "tired"]
    w = [0.03, 0.52, 0.06, 0.02, 0.02, 0.13, 0.04, 0.08, 0.03, 0.07]  # illustrative
    q = toks.index("it")
    css = (f".at-a{{animation:at-a {T}s infinite}}.at-b{{transform-box:fill-box;transform-origin:bottom;animation:at-b {T}s cubic-bezier(.2,.8,.3,1) infinite}}"
           f".at-o{{animation:at-o {T}s infinite}}.at-q{{animation:at-q {T}s infinite}}"
           f"@keyframes at-q{{0%,4%{{stroke-opacity:0}}8%,96%{{stroke-opacity:1}}100%{{stroke-opacity:0}}}}"
           f"@keyframes at-a{{0%,10%{{stroke-dashoffset:var(--len)}}35%,96%{{stroke-dashoffset:0}}100%{{stroke-dashoffset:var(--len)}}}}"
           f"@keyframes at-b{{0%,38%{{transform:scaleY(0)}}58%,96%{{transform:none}}100%{{transform:scaleY(0)}}}}"
           f"@keyframes at-o{{0%,62%{{opacity:0}}72%,96%{{opacity:1}}100%{{opacity:0}}}}"
           ".at-cap1{animation:at-c1 10s infinite}.at-cap2{animation:at-c2 10s infinite}.at-cap3{animation:at-c3 10s infinite}"
           "@keyframes at-c1{0%,36%{opacity:1}38%,100%{opacity:.25}}"
           "@keyframes at-c2{0%,37%{opacity:.25}39%,60%{opacity:1}62%,100%{opacity:.25}}"
           "@keyframes at-c3{0%,61%{opacity:.25}63%,100%{opacity:1}}")
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    x0, gap, TY = 60, 104, 300
    cx = [x0 + 47 + i * gap for i in range(len(toks))]
    for i, t in enumerate(toks):
        hi = i == q
        body += (f'<rect x="{cx[i] - 45}" y="{TY}" width="90" height="46" rx="10" fill="{"#13233f" if hi else CARD}" '
                 f'stroke="{ACCENT if hi else BORDER}" stroke-width="2" {"class=" + chr(34) + "at-q" + chr(34) if hi else ""}/>'
                 f'<text x="{cx[i]}" y="{TY + 30}" text-anchor="middle" class="t" font-size="18">{t}</text>')
    # arcs from the query to every token, width = weight; dashoffset draws them in
    for i in range(len(toks)):
        if i == q:
            continue
        x1, x2 = cx[q], cx[i]
        h = 40 + abs(x2 - x1) * 0.35
        d = f"M{x1},{TY} C{x1},{TY - h} {x2},{TY - h} {x2},{TY}"
        ln = int(abs(x2 - x1) * 1.4 + h)
        body += (f'<path class="at-a" style="--len:{ln}" d="{d}" fill="none" stroke="{ACCENT}" '
                 f'stroke-width="{1 + w[i] * 22:.1f}" stroke-opacity="{0.25 + w[i] * 1.4:.2f}" stroke-linecap="round" '
                 f'stroke-dasharray="{ln}" stroke-dashoffset="0"/>')
    # weight bars under the tokens
    for i in range(len(toks)):
        hb = w[i] * 230
        body += (f'<rect class="at-b" x="{cx[i] - 22}" y="{TY + 70 + 125 - hb:.0f}" width="44" height="{hb:.0f}" rx="5" '
                 f'fill="{GREEN if i == 1 else ACCENT}" opacity="{1 if i == 1 else .6}"/>'
                 f'<text x="{cx[i]}" y="{TY + 216}" text-anchor="middle" class="mu" font-size="13">{w[i]:.2f}</text>')
    body += f'<line x1="{x0}" y1="{TY + 195}" x2="{cx[-1] + 45}" y2="{TY + 195}" stroke="{BORDER}"/>'
    body += (f'<g class="at-o"><rect x="{cx[q] - 120}" y="{TY - 236}" width="240" height="52" rx="12" fill="#13233f" stroke="{GREEN}" stroke-width="2"/>'
             f'<text x="{cx[q]}" y="{TY - 204}" text-anchor="middle" fill="{LIGHT}" font-size="17" font-weight="600">out(it) = Σ wᵢ · vᵢ  ≈ v(cat)</text></g>')
    for j, (c, s) in enumerate((("at-cap1", "1 · score each token: q(it) · kᵢ / √d"),
                                ("at-cap2", "2 · softmax turns scores into weights"),
                                ("at-cap3", "3 · output = weighted mix of values"))):
        body += f'<text class="{c}" x="{60 + j * 360}" y="30" fill="{TEXT}" font-weight="700" font-size="17">{s}</text>'
    body += (f'<text x="60" y="568" class="mu" font-size="13">Each word carries a query q, a key k and a value v: three learned projections of its embedding '
             f'(d = their length).</text>'
             f'<text x="60" y="590" class="mu" font-size="13">vᵢ is word i’s value, so the output is mostly the value of “cat”. '
             f'Self-attention (Vaswani et al., 2017); weights are illustrative.</text>')
    write("attention", css, body)


# ── pipeline: how a deck is built; edges draw in, packets travel ──────────────
def fig_pipeline():
    T = 8
    nodes = [  # id, x, y, title, mono, tip
        ("tpl", 40, 120, "slides.tpl.qmd", "you + agent", "The deck source: Markdown plus FIG tokens where figures go."),
        ("gen", 40, 330, "make_figures.py", "→ images/*.svg", "Generates every animated SVG from data; rerun after edits."),
        ("bld", 360, 225, "build_deck.py", "inline figures", "Replaces FIG tokens with the SVG markup so links and hovers stay live."),
        ("md", 660, 225, "slides.qmd", "→ quarto render", "Generated; quarto render turns it into the reveal.js deck. Rebuilt on every build, so never edit it by hand."),
        ("html", 940, 70, "HTML", "deck server · Pages", "slides.html, served live on :8093 and published on GitHub Pages; also one self-contained file. Animations and hover work here."),
        ("pdf", 940, 225, "PDF", "static frame", "reveal.js print view, printed by Chrome. Shows each figure's static frame."),
        ("pptx", 940, 380, "PPTX", "editable shapes", "Text and shapes become native, editable PowerPoint objects."),
    ]
    pos = {n[0]: n for n in nodes}
    W, H = 200, 86
    edges = [("tpl", "bld"), ("gen", "bld"), ("bld", "md"), ("md", "html"), ("md", "pdf"), ("md", "pptx")]
    css = ".pl-n{cursor:help}.pl-n:hover rect{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += (f'<defs><marker id="pl-a" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto">'
             f'<path d="M0,0 L8,4 L0,8 z" fill="{ACCENT}"/></marker></defs>')
    for j, (a, b) in enumerate(edges):
        _, ax, ay, *_ = pos[a]
        _, bx, by, *_ = pos[b]
        x1, y1, x2, y2 = ax + W, ay + H / 2, bx - 8, by + H / 2
        mx = (x1 + x2) / 2
        d = f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"
        ln = int(math.hypot(x2 - x1, y2 - y1) * 1.15)
        stage = 0 if b == "bld" else 1 if b == "md" else 2
        s0, s1 = stage * 22, stage * 22 + 18
        e, p = f"pl-e{j}", f"pl-p{j}"
        css += (f".{e}{{animation:{e} {T}s infinite}}@keyframes {e}{{0%,{s0}%{{stroke-dashoffset:{ln};opacity:0}}{s0 + 1}%{{opacity:1}}{s1}%,94%{{stroke-dashoffset:0;opacity:1}}100%{{stroke-dashoffset:{ln};opacity:0}}}}"
                f".{p}{{offset-path:path('{d}');animation:{p} {T}s linear infinite;opacity:0}}"
                f"@keyframes {p}{{0%,{s1}%{{offset-distance:0%;opacity:0}}{s1 + 2}%{{opacity:1}}{s1 + 20}%{{offset-distance:100%;opacity:1}}{s1 + 22}%,100%{{offset-distance:100%;opacity:0}}}}")
        body += (f'<path class="{e}" d="{d}" fill="none" stroke="{ACCENT}" stroke-width="2.5" '
                 f'stroke-dasharray="{ln}" stroke-dashoffset="0" marker-end="url(#pl-a)"/>'
                 f'<circle class="{p}" cx="0" cy="0" r="6" fill="{LIGHT}"/>')
    for nid, x, y, title, mono, t in nodes:
        col = GREEN if nid in ("html", "pdf", "pptx") else ACCENT if nid == "bld" else BORDER
        body += (f'<g class="pl-n" {tip(title, t)}><rect x="{x}" y="{y}" width="{W}" height="{H}" rx="14" fill="{CARD}" stroke="{col}" stroke-width="2"/>'
                 f'<text x="{x + 18}" y="{y + 36}" class="t" font-size="19">{title}</text>'
                 f'<text x="{x + 18}" y="{y + 62}" class="m" font-size="14">{esc(mono)}</text></g>')
    body += (f'<text x="40" y="540" class="t" font-size="19">Figures are code.</text>'
             f'<text x="40" y="568" class="d" font-size="16">Change the data or the generator, rerun two scripts, and every export updates.</text>')
    write("pipeline", css, body)


# ── loop: the feedback loop; a dot orbits, each stage lights up in turn ───────
def fig_loop():
    T = 10
    cx, cy, r = 580, 300, 195
    steps = [("build", "agent writes the deck", "slide-deck skill", -90),
             ("render", "live server reloads", "scripts/start.sh", 0),
             ("comment", "you select text → 💬", "comments.json", 90),
             ("address", "agent folds feedback in", "address-feedback skill", 180)]
    css = (f".lp-o{{transform-origin:{cx}px {cy}px;animation:lp-o {T}s linear infinite}}"
           f"@keyframes lp-o{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}")
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{BORDER}" stroke-width="3" stroke-dasharray="2 10" stroke-linecap="round"/>'
    body += f'<g class="lp-o"><circle cx="{cx}" cy="{cy - r}" r="9" fill="{ACCENT}"/><circle cx="{cx}" cy="{cy - r}" r="17" fill="{ACCENT}" opacity=".25"/></g>'
    for i, (name, desc, mono, ang) in enumerate(steps):
        a = math.radians(ang)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        w = 300
        bx = x - w / 2 + (175 if ang == 0 else -175 if ang == 180 else 0)
        by = y - 45 + (-28 if ang == -90 else 28 if ang == 90 else 0)
        k = f"lp-s{i}"
        p0 = i * 25
        lit = (f"0%,20%{{stroke:{ACCENT}}}24%,100%{{stroke:{BORDER}}}" if i == 0 else
               f"0%,{p0 - 1}%{{stroke:{BORDER}}}{p0 + 2}%,{p0 + 20}%{{stroke:{ACCENT}}}{p0 + 24}%,100%{{stroke:{BORDER}}}")
        css += f".{k}{{animation:{k} {T}s infinite}}@keyframes {k}{{{lit}}}"
        body += (f'<rect class="{k}" x="{bx:.0f}" y="{by:.0f}" width="{w}" height="90" rx="14" fill="{CARD}" stroke="{BORDER}" stroke-width="2"/>'
                 f'<text x="{bx + 20:.0f}" y="{by + 32:.0f}" class="t" font-size="20">{name}</text>'
                 f'<text x="{bx + 20:.0f}" y="{by + 56:.0f}" class="d" font-size="15">{desc}</text>'
                 f'<text x="{bx + 20:.0f}" y="{by + 78:.0f}" class="m" font-size="13">{esc(mono)}</text>')
    body += (f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" class="t" font-size="22">one deck, many rounds</text>'
             f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" class="d" font-size="15">build, look, comment, repeat</text>')
    write("loop", css, body)


# ── driving: one planning step at an intersection (sample, predict, check, drive) ──
def car_svg(color, ghost=False):
    """A top-down car drawn around its centre, nose up (-y)."""
    op = ' opacity=".45"' if ghost else ""
    return (f'<g{op} transform="scale(1.4)"><rect x="-15" y="-26" width="30" height="52" rx="9" fill="{color}" stroke="#0b0b0b" stroke-width="2"/>'
            f'<path d="M-11,-12 L11,-12 L9,-3 L-9,-3 Z" fill="#0b1626" opacity=".85"/>'
            f'<path d="M-10,12 L10,12 L11,19 L-11,19 Z" fill="#0b1626" opacity=".7"/></g>')


def ped_svg(color):
    return (f'<g transform="scale(1.4)"><circle cx="0" cy="0" r="9" fill="{color}" stroke="#0b0b0b" stroke-width="2"/>'
            f'<circle cx="0" cy="-1" r="4.5" fill="#3a2a1a"/></g>')


def polyline(pts):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def arc_pts(p0, ctrl, p1, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * ctrl[0] + u * u * p1[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * ctrl[1] + u * u * p1[1]) for u in (i / n for i in range(n + 1))]


def frac_at(pts, target):
    """Fraction of the polyline's length at the vertex closest to target."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total, run, best = sum(seg), 0.0, (1e9, 0.0)
    for i, p in enumerate(pts):
        best = min(best, (math.dist(p, target), run / total))
        if i < len(seg):
            run += seg[i]
    return best[1]


def fig_intersection():
    T = 16
    cx, cy, L = 390, 300, 80                    # centre, road half-width (two lanes each way)
    ego0 = (430, 462)                           # northbound lane, behind the stop line
    straight = [ego0, (430, 10)]
    left = [ego0, (430, 360)] + arc_pts((430, 360), (430, 260), (340, 260))[1:] + [(10, 260)]
    right = [ego0, (430, 390)] + arc_pts((430, 390), (430, 340), (480, 340))[1:] + [(775, 340)]
    crash, near = (350, 260), (510, 340)        # conflict points
    onc = [(350, -60), (350, 660)]              # oncoming car, southbound lane
    ped = [(510, 430), (510, 175)]              # pedestrian on the east crosswalk
    f_left, f_right = frac_at(left, crash), frac_at(right, near)
    f_onc = (crash[1] + 60) / 720
    f_ped = (ped[0][1] - near[1]) / (ped[0][1] - ped[1][1])
    P = lambda x: f"{x * 100:.1f}%"
    css = ""
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    # roads, lane markings, stop line, crosswalk
    body += (f'<rect x="{cx - L}" y="0" width="{2 * L}" height="600" fill="#1c1f24"/>'
             f'<rect x="0" y="{cy - L}" width="780" height="{2 * L}" fill="#1c1f24"/>'
             f'<path d="M{cx},0 V{cy - L - 30} M{cx},{cy + L + 30} V600 M0,{cy} H{cx - L - 30} M{cx + L + 30},{cy} H780" '
             f'stroke="{YELLOW}" stroke-width="2" stroke-dasharray="14 12" opacity=".6"/>'
             f'<line x1="{cx}" y1="{cy + L + 22}" x2="{cx + L}" y2="{cy + L + 22}" stroke="#e8e8e8" stroke-width="5"/>')
    for i in range(9):
        body += f'<rect x="{cx + L + 20}" y="{cy - L + 6 + i * 17.5}" width="40" height="9" fill="#e8e8e8" opacity=".55"/>'
    # predicted motion of the others (dashed)
    body += (f'<g {tip("Prediction", "Where the planner expects the other road users to go in the next few seconds.")}>'
             f'<path class="ix-pr" d="{polyline(onc)}" fill="none" stroke="{ORANGE}" stroke-width="3" stroke-dasharray="4 9" opacity=".8"/>'
             f'<path class="ix-pr" d="{polyline(ped)}" fill="none" stroke="{YELLOW}" stroke-width="3" stroke-dasharray="4 9" opacity=".8"/></g>')
    css += f".ix-pr{{animation:ix-pr {T}s infinite}}@keyframes ix-pr{{0%,12%{{opacity:0}}16%,100%{{opacity:.8}}}}"
    # three candidates: static frame shows the verdict colours
    cands = [("left", left, RED, "left: collides", "Turning left crosses the oncoming lane exactly when the oncoming car arrives.", .46),
             ("straight", straight, GREEN, "straight: clear", "Nothing is predicted to cross this path; the planner picks it.", .66),
             ("right", right, ORANGE, "right: blocks pedestrian", "Turning right reaches the crosswalk while the pedestrian is on it.", .62)]
    for k, (name, pts, col, label, why, tv) in enumerate(cands):
        c = f"ix-c{k}"
        css += (f".{c}{{animation:{c} {T}s infinite}}@keyframes {c}{{0%{{stroke-dashoffset:1;stroke:{LIGHT}}}"
                f"10%,{P(tv - .01)}{{stroke-dashoffset:0;stroke:{LIGHT}}}{P(tv + .01)},100%{{stroke-dashoffset:0;stroke:{col}}}}}")
        body += (f'<path class="{c}" d="{polyline(pts)}" fill="none" stroke="{col}" stroke-width="5" stroke-linecap="round" '
                 f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="0" opacity=".9" {tip(label, why)}/>')
    lab = [("left", RED, "✕ collision", 16, 206), ("straight", GREEN, "✓ clear", 446, 34), ("right", ORANGE, "✕ pedestrian", 640, 368)]
    for k, ((name, col, verdict, x, y), (_, _, _, _, _, tv)) in enumerate(zip(lab, cands)):
        v = f"ix-v{k}"
        css += f".{v}{{animation:{v} {T}s infinite}}@keyframes {v}{{0%,{P(tv)}{{opacity:0}}{P(tv + .02)},100%{{opacity:1}}}}"
        body += (f'<text x="{x}" y="{y}" class="t" font-size="20">{name}</text>'
                 f'<text class="{v}" x="{x}" y="{y + 23}" font-size="18" font-weight="700" fill="{col}">{verdict}</text>')
    # rollout 1 (left): ghost ego and ghost oncoming car meet at the crash point
    s1, e1 = .28, .46
    css += (f".ix-g1{{offset-path:path('{polyline(left)}');offset-rotate:auto 90deg;animation:ix-g1 {T}s linear infinite}}"
            f"@keyframes ix-g1{{0%,{P(s1)}{{offset-distance:0%;opacity:0}}{P(s1 + .01)}{{opacity:1}}{P(e1)},{P(e1 + .05)}{{offset-distance:{f_left * 100:.1f}%;opacity:1}}{P(e1 + .07)},100%{{offset-distance:{f_left * 100:.1f}%;opacity:0}}}}"
            f".ix-g2{{offset-path:path('{polyline(onc)}');offset-rotate:auto 90deg;animation:ix-g2 {T}s linear infinite}}"
            f"@keyframes ix-g2{{0%,{P(s1)}{{offset-distance:0%;opacity:0}}{P(s1 + .01)}{{opacity:1}}{P(e1)},{P(e1 + .05)}{{offset-distance:{f_onc * 100:.1f}%;opacity:1}}{P(e1 + .07)},100%{{offset-distance:{f_onc * 100:.1f}%;opacity:0}}}}"
            f".ix-bang{{transform-box:fill-box;transform-origin:center;animation:ix-bang {T}s infinite}}"
            f"@keyframes ix-bang{{0%,{P(e1 - .005)}{{opacity:0;transform:scale(.2)}}{P(e1 + .01)}{{opacity:1;transform:scale(1.25)}}{P(e1 + .04)},100%{{opacity:1;transform:scale(1)}}}}")
    body += f'<g class="ix-g1" style="offset-distance:0%;opacity:0">{car_svg(ACCENT, True)}</g>'
    body += f'<g class="ix-g2" style="offset-distance:0%;opacity:0">{car_svg(ORANGE, True)}</g>'
    star = " ".join(f"{crash[0] + (26 if i % 2 == 0 else 11) * math.cos(i * math.pi / 8):.1f},{crash[1] + (26 if i % 2 == 0 else 11) * math.sin(i * math.pi / 8):.1f}" for i in range(16))
    body += (f'<g class="ix-bang" {tip("Collision", "The rollout of the left turn hits the oncoming car, so the planner rejects it.")}>'
             f'<polygon points="{star}" fill="{RED}" stroke="#ffd1cf" stroke-width="2"/>'
             f'<text x="{crash[0]}" y="{crash[1] + 6}" text-anchor="middle" font-size="16" font-weight="800" fill="#fff">!</text></g>')
    # rollout 2 (right): ghost ego reaches the crosswalk while the pedestrian is on it
    s2, e2 = .48, .62
    css += (f".ix-g3{{offset-path:path('{polyline(right)}');offset-rotate:auto 90deg;animation:ix-g3 {T}s linear infinite}}"
            f"@keyframes ix-g3{{0%,{P(s2)}{{offset-distance:0%;opacity:0}}{P(s2 + .01)}{{opacity:1}}{P(e2)},{P(e2 + .04)}{{offset-distance:{max(f_right - .04, 0) * 100:.1f}%;opacity:1}}{P(e2 + .06)},100%{{offset-distance:{max(f_right - .04, 0) * 100:.1f}%;opacity:0}}}}"
            f".ix-g4{{offset-path:path('{polyline(ped)}');offset-rotate:0deg;animation:ix-g4 {T}s linear infinite}}"
            f"@keyframes ix-g4{{0%,{P(s2)}{{offset-distance:0%;opacity:0}}{P(s2 + .01)}{{opacity:.6}}{P(e2)},{P(e2 + .04)}{{offset-distance:{f_ped * 100:.1f}%;opacity:.6}}{P(e2 + .06)},100%{{offset-distance:{f_ped * 100:.1f}%;opacity:0}}}}"
            f".ix-warn{{animation:ix-warn {T}s infinite}}@keyframes ix-warn{{0%,{P(e2 - .005)}{{opacity:0}}{P(e2 + .01)},100%{{opacity:1}}}}")
    body += f'<g class="ix-g3" style="offset-distance:0%;opacity:0">{car_svg(ACCENT, True)}</g>'
    body += f'<g class="ix-g4" style="offset-distance:0%;opacity:0">{ped_svg(YELLOW)}</g>'
    body += (f'<g class="ix-warn" {tip("Too close", "The right-turn rollout reaches the crosswalk with the pedestrian still on it.")}>'
             f'<circle cx="{near[0]}" cy="{near[1]}" r="24" fill="none" stroke="{ORANGE}" stroke-width="3" stroke-dasharray="6 5"/></g>')
    # drive: the real actors move; ego takes the clear straight path
    s3, e3 = .70, .96
    css += (f".ix-ego{{offset-path:path('{polyline(straight)}');offset-rotate:auto 90deg;animation:ix-ego {T}s ease-in infinite}}"
            f"@keyframes ix-ego{{0%,{P(s3)}{{offset-distance:0%;opacity:1}}{P(e3)}{{offset-distance:100%;opacity:1}}{P(e3 + .02)}{{opacity:0}}100%{{offset-distance:0%;opacity:0}}}}"
            f".ix-onc{{offset-path:path('{polyline(onc)}');offset-rotate:auto 90deg;animation:ix-onc {T}s linear infinite}}"
            f"@keyframes ix-onc{{0%,{P(s3)}{{offset-distance:10%}}{P(e3)},100%{{offset-distance:100%}}}}"
            f".ix-ped{{offset-path:path('{polyline(ped)}');offset-rotate:0deg;animation:ix-ped {T}s linear infinite}}"
            f"@keyframes ix-ped{{0%,{P(s3)}{{offset-distance:0%}}{P(e3)},100%{{offset-distance:100%}}}}")
    body += f'<g class="ix-onc" style="offset-distance:10%" {tip("Oncoming car", "Drives straight through, southbound.")}>{car_svg(ORANGE)}</g>'
    body += f'<g class="ix-ped" style="offset-distance:0%" {tip("Pedestrian", "Crosses the east road on the crosswalk.")}>{ped_svg(YELLOW)}</g>'
    body += f'<g class="ix-ego" style="offset-distance:0%" {tip("Ego vehicle", "The car we plan for. It waits at the stop line, then drives the chosen path.")}>{car_svg(ACCENT)}</g>'
    # step panel on the right; each step lights up in its window
    steps = [("1", "Sample", "left, straight, right", 0, .14),
             ("2", "Predict", "oncoming car, pedestrian", .14, .28),
             ("3", "Roll out left", "hits the oncoming car", .28, .47),
             ("4", "Roll out right", "pedestrian on the crosswalk", .48, .63),
             ("5", "Pick and drive", "straight is clear", .64, 1.0)]
    for i, (n, head, desc, a, b) in enumerate(steps):
        y = 14 + i * 92
        k = f"ix-s{i}"
        lit = (f"0%,{P(a - .005)}{{stroke:{BORDER};fill:{CARD}}}" if a > 0 else "") + (
            f"{P(a)},{P(b - .005)}{{stroke:{ACCENT};fill:#13233f}}" + (f"{P(b)},100%{{stroke:{BORDER};fill:{CARD}}}" if b < 1 else ""))
        css += f".{k}{{animation:{k} {T}s infinite}}@keyframes {k}{{{lit}}}"
        body += (f'<rect class="{k}" x="800" y="{y}" width="345" height="80" rx="12" fill="{CARD}" stroke="{BORDER}" stroke-width="2"/>'
                 f'<circle cx="832" cy="{y + 30}" r="16" fill="{ACCENT}"/><text x="832" y="{y + 36}" text-anchor="middle" font-size="17" font-weight="800" fill="#fff">{n}</text>'
                 f'<text x="860" y="{y + 37}" class="t" font-size="21">{head}</text>'
                 f'<text x="860" y="{y + 64}" class="d" font-size="18">{desc}</text>')
    for k, line in enumerate(("Rollout: move the car along one path in",
                              "simulation, next to the predicted others.",
                              "Here a path fails if it hits someone; real",
                              "planners also score comfort and progress.",
                              "Hand-placed scene, not a real planner.")):
        body += f'<text x="800" y="{490 + k * 21}" class="mu" font-size="14">{line}</text>'
    write("intersection", css, body)


# ── Static overviews: no animation, the whole story in one frame ─────────────

REGIONS = (("NA", {"sf", "mtv", "palo", "bayarea", "phoenix", "vegas", "ny", "boston", "pitt",
                   "miami", "detroit", "dc", "austin"}),
           ("EU", {"karlsruhe", "munich", "ingolstadt", "london", "germany", "europe"}),
           ("Asia", {"singapore", "china"}))
LIC = {  # license class: (label, colour)
    "open": ("commercial use allowed", GREEN),
    "nc": ("non-commercial", ORANGE),
    "custom": ("custom terms", PURPLE),
}


def lic_class(lic):
    if lic.startswith("CC BY") and "NC" not in lic:
        return "open"
    if "Custom (members)" in lic or "Research" in lic:
        return "custom"
    return "nc"


# ── licenses: a comparison matrix (rows = datasets, columns = facets) ────────
def fig_licenses():
    rows = sorted(datasets(), key=lambda r: (int(r["year"]), r["dataset"]))
    x_name, x_year, x_reg, x_hrs, x_lic = 40, 270, 350, 560, 820
    top, rh = 92, 30
    css = ".lc-r{cursor:help}.lc-r:hover .lc-bg{fill:#1d2633}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    for x, h in ((x_name, "dataset"), (x_year, "year"), (x_reg, "recorded in"),
                 (x_hrs, "hours recorded (log)"), (x_lic, "license")):
        body += f'<text x="{x}" y="{top - 30}" class="mu" font-size="13" letter-spacing="1.5">{h.upper()}</text>'
    for i, (reg, _) in enumerate(REGIONS):
        body += f'<text x="{x_reg + 12 + i * 62}" y="{top - 10}" class="mu" font-size="12" text-anchor="middle">{reg}</text>'
    body += f'<line x1="40" y1="{top - 2}" x2="1120" y2="{top - 2}" stroke="{BORDER}"/>'
    lo, hi = math.log10(0.1), math.log10(2000)
    for i, r in enumerate(rows):
        y = top + i * rh
        cls = lic_class(r["license"])
        col = LIC[cls][1]
        pts = set(r["points"].split())
        body += f'<g class="lc-r" {ds_tip(r)}><rect class="lc-bg" x="30" y="{y + 2}" width="1100" height="{rh - 4}" rx="6" fill="{BG if i % 2 else CARD}"/>'
        body += f'<text x="{x_name}" y="{y + 21}" class="t" font-size="16">{esc(r["dataset"])}</text>'
        body += f'<text x="{x_year}" y="{y + 21}" class="d" font-size="15">{r["year"]}</text>'
        for j, (_, cities) in enumerate(REGIONS):
            on = bool(pts & cities)
            body += (f'<circle cx="{x_reg + 12 + j * 62}" cy="{y + 15}" r="7" fill="{ACCENT if on else "none"}" '
                     f'stroke="{ACCENT if on else BORDER}" stroke-width="2"/>')
        if r["hours"]:
            w = 200 * (math.log10(float(r["hours"])) - lo) / (hi - lo)
            body += (f'<rect x="{x_hrs}" y="{y + 8}" width="{w:.0f}" height="14" rx="3" fill="{LIGHT}" opacity=".85"/>'
                     f'<text x="{x_hrs + w + 8:.0f}" y="{y + 20}" class="m" font-size="12">{fmt(r["hours"])}</text>')
        else:
            body += f'<text x="{x_hrs}" y="{y + 20}" class="mu" font-size="13">not reported</text>'
        body += (f'<rect x="{x_lic}" y="{y + 5}" width="12" height="20" rx="3" fill="{col}"/>'
                 f'<text x="{x_lic + 22}" y="{y + 21}" class="d" font-size="14">{esc(r["license"])}</text></g>')
    ly = top + len(rows) * rh + 22
    for k, (cls, (label, col)) in enumerate(LIC.items()):
        n = sum(lic_class(r["license"]) == cls for r in rows)
        x = 40 + k * 300
        body += (f'<rect x="{x}" y="{ly - 12}" width="12" height="14" rx="3" fill="{col}"/>'
                 f'<text x="{x + 20}" y="{ly}" class="d" font-size="14"><tspan class="t">{n}</tspan>  {label}</text>')
    body += (f'<text x="40" y="{ly + 26}" class="mu" font-size="13">Class from the license label: CC BY without NC = commercial; any NC term, '
             f'even on request = non-commercial; members-only or research = custom. Rough, not legal advice.</text>')
    write("licenses", css, body)


# ── lineage: four papers that changed the default, one card each ─────────────
PAPERS = [  # year, short name, authors, venue, what changed, the default it replaced, headline, label, deck
    (2012, "AlexNet", "Krizhevsky, Sutskever, Hinton", "NIPS 2012",
     ["Deep CNNs trained on GPUs", "win ImageNet by a wide margin"], "hand-designed features", "15.3%", "top-5 error vs 26.2% runner-up", "paper-reviews/alexnet"),
    (2015, "ResNet", "He, Zhang, Ren, Sun", "CVPR 2016",
     ["Identity shortcuts let nets go", "152 layers deep and still train"], "nets of about 20 layers", "3.57%", "top-5 error, ImageNet test", "paper-reviews/resnet"),
    (2017, "Transformer", "Vaswani et al.", "NIPS 2017",
     ["Attention alone, no recurrence:", "every word reads every other"], "recurrent nets for text", "28.4", "BLEU, WMT 2014 EN-DE", "paper-reviews/attention"),
    (2020, "NeRF", "Mildenhall, Srinivasan, Tancik et al.", "ECCV 2020",
     ["One MLP stores one scene;", "rendering it is differentiable"], "meshes and voxel grids", "31.01", "PSNR on synthetic scenes", "paper-reviews/nerf"),
]


def fig_lineage():
    cols = [ACCENT, GREEN, PURPLE, ORANGE]
    y0, x0, x1 = 118, 90, 1070
    yr0, yr1 = 2011, 2021
    X = lambda yr: x0 + (yr - yr0) / (yr1 - yr0) * (x1 - x0)
    css = ".ln-c{cursor:help}.ln-c:hover rect.ln-b{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{BORDER}" stroke-width="3"/>'
    for yr in range(yr0 + 1, yr1):
        body += (f'<line x1="{X(yr):.0f}" y1="{y0 - 6}" x2="{X(yr):.0f}" y2="{y0 + 6}" stroke="{BORDER}" stroke-width="2"/>'
                 f'<text x="{X(yr):.0f}" y="{y0 - 16}" class="mu" font-size="13" text-anchor="middle">{yr}</text>')
    w, gap = 248, 10
    for i, (yr, name, auth, venue, what, was, num, lab, deck) in enumerate(PAPERS):
        c = cols[i]
        bx = 40 + i * (w + gap) + (i * 6)
        cx = bx + w / 2
        body += (f'<path d="M{X(yr):.0f},{y0} V{y0 + 40} H{cx:.0f} V{y0 + 62}" fill="none" stroke="{c}" stroke-width="2"/>'
                 f'<circle cx="{X(yr):.0f}" cy="{y0}" r="9" fill="{c}"/>')
        t = tip(f"{name} ({venue})", f"{auth}. Deck: decks/{deck}/")
        by = y0 + 62
        body += (f'<g class="ln-c" {t}><rect class="ln-b" x="{bx}" y="{by}" width="{w}" height="330" rx="14" fill="{CARD}" stroke="{c}" stroke-width="2"/>'
                 f'<rect x="{bx}" y="{by}" width="{w}" height="6" rx="3" fill="{c}"/>'
                 f'<text x="{bx + 20}" y="{by + 44}" class="t" font-size="26">{name}</text>'
                 f'<text x="{bx + 20}" y="{by + 70}" class="d" font-size="14">{esc(venue)}</text>'
                 f'<text x="{bx + 20}" y="{by + 120}" font-size="14.5" fill="{TEXT}">{esc(what[0])}</text>'
                 f'<text x="{bx + 20}" y="{by + 142}" font-size="14.5" fill="{TEXT}">{esc(what[1])}</text>'
                 f'<text x="{bx + 20}" y="{by + 168}" class="mu" font-size="13.5">replaced: {esc(was)}</text>'
                 f'<line x1="{bx + 20}" y1="{by + 186}" x2="{bx + w - 20}" y2="{by + 186}" stroke="{BORDER}"/>'
                 f'<text x="{bx + 20}" y="{by + 240}" font-size="50" font-weight="800" fill="{c}">{num}</text>'
                 f'<text x="{bx + 20}" y="{by + 268}" class="d" font-size="14">{esc(lab)}</text>'
                 f'<text x="{bx + 20}" y="{by + 300}" class="m" font-size="12">decks/</text>'
                 f'<text x="{bx + 20}" y="{by + 317}" class="m" font-size="12">{deck}/</text></g>')
    body += (f'<text x="40" y="548" class="d" font-size="15">One card per paper-review deck in this repo, '
             f'placed on the year it appeared.</text>'
             f'<text x="40" y="572" class="mu" font-size="13">Each headline number uses that paper’s own metric and benchmark; '
             f'do not compare them across cards.</text>')
    write("lineage", css, body)


# ── architecture: what runs where when you serve and publish decks ───────────
def fig_architecture():
    cols = [  # title, colour, x, boxes: (name, detail, mono, tip)
        ("write", PURPLE, 40, [
            ("you + coding agent", "brief, review, comment", "", "You steer; the agent writes and rebuilds."),
            ("agent skills", "slide-deck, deck-feedback,", "address-feedback", "Instructions in .agents/skills/ that any coding agent can follow.")]),
        ("source", ACCENT, 320, [
            ("slides.tpl.qmd", "deck text + FIG tokens", "decks/<category>/<deck>/", "The deck source; build_deck.py generates slides.qmd from it."),
            ("make_figures.py + data/", "figures from data", "→ images/*.svg", "Every figure is code; rerun after edits."),
            ("comments.json", "open and resolved comments", "per deck, gitignored", "Written by the comment UI, read by the agent.")]),
        ("serve: 1 process", GREEN, 600, [
            ("deck server", "open this one: all decks", ":8093", "quarto/scripts/serve.py: serves every rendered deck and the index page, swaps re-rendered slides into open pages."),
            ("comments/exports", "API: edit mode, downloads", ":8094", "Same process, second port: comments.json, edit-mode saves and live previews, HTML, PPTX and PDF downloads."),
            ("quarto render", "re-renders a changed deck", "~2 s per deck", "The server's watcher runs quarto render on a deck whose sources changed, one deck at a time.")]),
        ("publish", ORANGE, 880, [
            ("exports/", "PDF · PPTX · HTML", "scripts/export.sh", "One file per deck and format."),
            ("GitHub Pages", "every deck, downloads opt-in", "on push to main", "Built by .github/workflows/pages.yml with scripts/build_site.sh; read-only, no comments or edit mode.")]),
    ]
    W, H, gap = 240, 112, 22
    css = ".ar-b{cursor:help}.ar-b:hover rect{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += (f'<defs><marker id="ar-a" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto">'
             f'<path d="M0,0 L8,4 L0,8 z" fill="{MUTED}"/></marker></defs>')
    body += f'<rect x="590" y="46" width="260" height="404" rx="18" fill="none" stroke="{GREEN}" stroke-opacity=".35" stroke-dasharray="6 6"/>'
    body += (f'<text x="720" y="476" class="mu" font-size="13" text-anchor="middle">this machine only; SLIDES_HOST=0.0.0.0</text>'
             f'<text x="720" y="494" class="mu" font-size="13" text-anchor="middle">opens it to the network</text>')
    for k, (title, c, x, boxes) in enumerate(cols):
        body += f'<text x="{x}" y="30" font-size="14" font-weight="700" letter-spacing="2" fill="{c}">{title.upper()}</text>'
        n = len(boxes)
        y0 = 60 + (3 - n) * (H + gap) / 2
        for i, (name, detail, mono, t) in enumerate(boxes):
            y = y0 + i * (H + gap)
            body += (f'<g class="ar-b" {tip(name, t)}><rect x="{x}" y="{y:.0f}" width="{W}" height="{H}" rx="14" fill="{CARD}" stroke="{c}" stroke-width="2"/>'
                     f'<text x="{x + 18}" y="{y + 36:.0f}" class="t" font-size="18">{esc(name)}</text>'
                     f'<text x="{x + 18}" y="{y + 62:.0f}" class="d" font-size="14">{esc(detail)}</text>'
                     f'<text x="{x + 18}" y="{y + 88:.0f}" class="m" font-size="13">{esc(mono)}</text></g>')
        if k < len(cols) - 1:
            ax = x + W + 6
            body += f'<line x1="{ax}" y1="296" x2="{ax + 24}" y2="296" stroke="{MUTED}" stroke-width="2.5" marker-end="url(#ar-a)"/>'
    write("architecture", css, body)


# ── deck types: a 2×2 map of what each deck type explains ────────────────────
def fig_deck_types():
    L, R, T, B = 120, 1100, 50, 520
    mx, my = (L + R) / 2, (T + B) / 2
    types = [  # name, x 0..1 (code → ideas), y 0..1 (one change → whole field), colour, ref, tip
        ("MR review", 0.16, 0.18, GREEN, "deck-mr-review.md", "One change: what it does, where to look hard, what could break."),
        ("Repo tour", 0.22, 0.80, ACCENT, "deck-repo-intro.md", "A whole codebase: run it, read it, know which file to change."),
        ("Tool demo", 0.38, 0.68, ORANGE, "deck-tool-presentation.md", "One tool: what it is, a live example, how to start."),
        ("Paper deep dive", 0.80, 0.22, PURPLE, "paper-deck.md", "One paper: the mechanism, the evidence, what to doubt."),
        ("Research overview", 0.80, 0.80, YELLOW, "deck-research-overview.md", "A field: the landscape, the open questions, what to read."),
    ]
    css = ".dt-n{cursor:help}.dt-n:hover rect{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    for qx, qy in ((L, T), (mx, T), (L, my), (mx, my)):
        body += f'<rect x="{qx + 4}" y="{qy + 4}" width="{(R - L) / 2 - 8}" height="{(B - T) / 2 - 8}" rx="16" fill="{CARD}" opacity=".55"/>'
    body += (f'<line x1="{L}" y1="{my}" x2="{R}" y2="{my}" stroke="{BORDER}" stroke-width="2"/>'
             f'<line x1="{mx}" y1="{T}" x2="{mx}" y2="{B}" stroke="{BORDER}" stroke-width="2"/>'
             f'<text x="{L}" y="{B + 34}" class="d" font-size="15">← about code</text>'
             f'<text x="{R}" y="{B + 34}" class="d" font-size="15" text-anchor="end">about ideas →</text>'
             f'<text x="{L - 28}" y="{B}" class="d" font-size="15" transform="rotate(-90 {L - 28} {B})">one change ·</text>'
             f'<text x="{L - 28}" y="{T}" class="d" font-size="15" text-anchor="end" transform="rotate(-90 {L - 28} {T})">· whole system or field</text>')
    for name, fx, fy, c, ref, t in types:
        x = L + fx * (R - L)
        y = B - fy * (B - T)
        w = 18 + len(name) * 11.5
        body += (f'<g class="dt-n" {tip(name, t + " Reference: " + ref)}>'
                 f'<circle cx="{x:.0f}" cy="{y:.0f}" r="34" fill="{c}" opacity=".14"/>'
                 f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{c}"/>'
                 f'<rect x="{x - w / 2:.0f}" y="{y + 18:.0f}" width="{w:.0f}" height="34" rx="17" fill="{BG}" stroke="{c}" stroke-width="2"/>'
                 f'<text x="{x:.0f}" y="{y + 41:.0f}" text-anchor="middle" class="t" font-size="17">{name}</text>'
                 f'<text x="{x:.0f}" y="{y + 72:.0f}" text-anchor="middle" class="m" font-size="12">{ref}</text></g>')
    write("deck-types", css, body)


# ── composition: three facets of the same fifteen datasets, one square each ──
CONTINENT = {"NA": REGIONS[0][1], "EU": REGIONS[1][1], "Asia": REGIONS[2][1]}


def continents(r):
    pts = set(r["points"].split())
    return " + ".join(c for c, keys in CONTINENT.items() if pts & keys)


def fig_composition():
    rows = sorted(datasets(), key=lambda r: (list(FAM).index(r["family"]), int(r["year"]), r["dataset"]))
    facets = [  # title, key(row) -> category, category order, category colour
        ("task", lambda r: FAM_LABEL[r["family"]], [FAM_LABEL[f] for f in FAM], {FAM_LABEL[f]: c for f, c in FAM.items()}),
        ("recorded in", continents, ["NA", "EU", "NA + Asia", "Asia", "NA + EU"], {}),
        ("license", lambda r: LIC[lic_class(r["license"])][0], [v[0] for v in LIC.values()], {v[0]: v[1] for v in LIC.values()}),
    ]
    S, G, X0s, TOP, RH = 26, 6, (40, 420, 800), 78, 84
    css = ".cp-ds{cursor:help}.cp-ds:hover rect{stroke:#fff;stroke-width:2.5}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    cells = {r["dataset"]: "" for r in rows}  # one group per dataset, so hover lights all three squares
    for (title, key, order, colour), x0 in zip(facets, X0s):
        body += (f'<text x="{x0}" y="34" class="mu" font-size="13" letter-spacing="1.5">{title.upper()}</text>'
                 f'<line x1="{x0}" y1="46" x2="{x0 + 330}" y2="46" stroke="{BORDER}"/>')
        for j, cat in enumerate(order):
            members = [r for r in rows if key(r) == cat]
            y = TOP + j * RH
            body += (f'<text x="{x0}" y="{y}" font-size="17" font-weight="700" fill="{colour.get(cat, TEXT)}">{esc(cat)}</text>'
                     f'<text x="{x0 + 330}" y="{y}" text-anchor="end" class="t" font-size="22">{len(members)}</text>')
            for k, r in enumerate(members):
                cells[r["dataset"]] += (f'<rect x="{x0 + k * (S + G)}" y="{y + 14}" width="{S}" height="{S}" rx="5" '
                                        f'fill="{FAM[r["family"]]}" stroke="{BG}" stroke-width="1.5"/>')
    for r in rows:
        body += f'<g class="cp-ds" {ds_tip(r)}>{cells[r["dataset"]]}</g>'
    body += (f'<text x="40" y="560" class="d" font-size="15">One square per dataset, coloured by its task. '
             f'Hover one: the same dataset lights up in all three columns.</text>'
             f'<text x="40" y="586" class="mu" font-size="13">Continents from the recording locations in data/datasets.csv; '
             f'license classes as on the licenses slide.</text>')
    write("composition", css, body)


# ── images: an annotated bar chart, one callout carries the claim ────────────
def fig_images():
    rows = sorted((r for r in datasets() if r["images"]), key=lambda r: -float(r["images"]))
    top, rest = rows[0], rows[1:]
    n_top, n_rest = float(top["images"]), sum(float(r["images"]) for r in rest)
    X0, X1, Y0, RH = 200, 1000, 64, 33
    vmax = math.ceil(n_top / 1e6) * 1e6
    xv = lambda v: X0 + v / vmax * (X1 - X0)
    css = ".im-b{cursor:help}.im-b:hover rect{stroke:#fff;stroke-width:2}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    yb = Y0 + len(rows) * RH + 64  # the combined bar sits below the others
    for m in range(int(vmax / 1e6) + 1):
        x = xv(m * 1e6)
        body += (f'<line x1="{x:.0f}" y1="{Y0 - 8}" x2="{x:.0f}" y2="{yb + 30}" stroke="{BORDER}" stroke-dasharray="3 6"/>'
                 f'<text x="{x:.0f}" y="{Y0 - 18}" text-anchor="middle" class="mu" font-size="13">{m}M</text>')
    for i, r in enumerate(rows):
        y = Y0 + i * RH
        v = float(r["images"])
        hot = r is top
        body += (f'<g class="im-b" {ds_tip(r)}><text x="{X0 - 14}" y="{y + 20}" text-anchor="end" '
                 f'class="{"t" if hot else "d"}" font-size="15">{esc(r["dataset"])}</text>'
                 f'<rect x="{X0}" y="{y + 6}" width="{max(xv(v) - X0, 2):.1f}" height="20" rx="4" fill="{FAM[r["family"]]}" '
                 f'opacity="{1 if hot else .6}"/>'
                 f'<text x="{max(xv(v), X0 + 2) + 10:.0f}" y="{y + 21}" class="m" font-size="13">{fmt(v)}</text></g>')
    body += (f'<line x1="{X0 - 150}" y1="{yb - 30}" x2="{X1 + 120}" y2="{yb - 30}" stroke="{BORDER}"/>'
             f'<text x="{X0 - 14}" y="{yb + 20}" text-anchor="end" class="t" font-size="15">other {len(rest)}, combined</text>')
    x = X0
    for r in reversed(rest):  # stacked: every other dataset, end to end
        w = xv(float(r["images"])) - X0
        body += (f'<g class="im-b" {ds_tip(r)}><rect x="{x:.1f}" y="{yb + 6}" width="{w:.1f}" height="20" '
                 f'fill="{FAM[r["family"]]}" opacity=".6" stroke="{BG}" stroke-width="1"/></g>')
        x += w
    body += f'<text x="{x + 10:.0f}" y="{yb + 21}" class="m" font-size="13">{fmt(n_rest)}</text>'
    # callout: the ratio, pointing at both bars
    cx, cy = xv(n_rest) + 150, Y0 + 2.4 * RH
    body += (f'<path d="M{xv(n_top) - 40:.0f},{Y0 + 28} L{cx + 110:.0f},{cy}" stroke="{YELLOW}" stroke-width="1.5" fill="none"/>'
             f'<path d="M{xv(n_rest) + 4:.0f},{yb + 6} L{cx:.0f},{cy + 60}" stroke="{YELLOW}" stroke-width="1.5" fill="none"/>'
             f'<rect x="{cx - 20:.0f}" y="{cy:.0f}" width="300" height="60" rx="10" fill="{CARD}" stroke="{YELLOW}" stroke-width="1.5"/>'
             f'<text x="{cx:.0f}" y="{cy + 26:.0f}" font-size="18" font-weight="700" fill="{YELLOW}">{n_top / n_rest:.1f}× the other {len(rest)}</text>'
             f'<text x="{cx:.0f}" y="{cy + 47:.0f}" class="d" font-size="14">{esc(top["dataset"])}: {fmt(n_top)} images</text>')
    missing = sorted(r["dataset"] for r in datasets() if not r["images"])
    body += (f'<text x="40" y="566" class="mu" font-size="13">Image counts as each paper reports them: some count every camera frame, '
             f'others one image per annotated sample, so the ratio is rough.</text>'
             f'<text x="40" y="586" class="mu" font-size="13">No count in the data for {", ".join(missing)}.</text>')
    write("images", css, body)


# ── token: before / after, one FIG token in the source becomes a live figure ──
def fig_token():
    tpl = (HERE / "slides.tpl.qmd").read_text().split("\n")
    i = next(k for k, l in enumerate(tpl) if l.strip() == "<!--FIG:hours-->")
    head = next(l for l in reversed(tpl[:i]) if l.startswith("## "))
    svg = (OUT / "hours.svg").read_text().strip().split("\n")
    short = lambda s, n: s if len(s) <= n else s[:n - 1] + "…"
    W, PY, PH = 330, 70, 380
    panels = [(40, "slides.tpl.qmd", "you edit", ACCENT), (415, "slides.qmd", "build_deck.py writes", GREEN),
              (790, "the slide", "quarto render draws", ORANGE)]
    css = ".tk-p{cursor:help}.tk-p:hover rect.tk-f{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += (f'<defs><marker id="tk-a" markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto">'
             f'<path d="M0,0 L8,4 L0,8 z" fill="{MUTED}"/></marker></defs>')
    tips = ["The deck source. A figure is one HTML comment naming the SVG in images/.",
            "Generated: the token is replaced by the whole of images/hours.svg, inline, so links and hover cards keep working. Rebuilt on every build, so never edit it by hand.",
            "What the reader sees: the inlined SVG, sized to 980 by 507 px."]
    for (x, name, sub, c), t in zip(panels, tips):
        body += (f'<g class="tk-p" {tip(name, t)}><rect class="tk-f" x="{x}" y="{PY}" width="{W}" height="{PH}" rx="14" fill="{CARD}" stroke="{c}" stroke-width="2"/>'
                 f'<text x="{x + 18}" y="{PY - 16}" class="t" font-size="18">{name}</text>'
                 f'<text x="{x + W}" y="{PY - 16}" text-anchor="end" class="mu" font-size="14">{sub}</text></g>')
    for x in (378, 753):
        body += f'<line x1="{x}" y1="{PY + PH / 2}" x2="{x + 24}" y2="{PY + PH / 2}" stroke="{MUTED}" stroke-width="2.5" marker-end="url(#tk-a)"/>'
    mono = 'font-family="JetBrains Mono, monospace" style="font-variant-ligatures:none;font-feature-settings:&apos;calt&apos; 0"'
    lit = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    code = lambda x, y, s, fill=SUB: f'<text x="{x}" y="{y}" {mono} font-size="13" fill="{fill}">{lit(short(s, 38))}</text>'
    kb = len((OUT / "hours.svg").read_bytes()) / 1024
    # before: the slide as written
    x, y = 58, PY + 40
    for line, fill in (("---", MUTED), ("", None), (head[:22], TEXT), ("   " + head[22:], TEXT), ("", None),
                       ("<!--FIG:hours-->", LIGHT), ("", None), ("---", MUTED)):
        if line and "FIG" in line:
            body += f'<rect x="{x - 8}" y="{y - 17}" width="{W - 20}" height="26" rx="5" fill="#13233f" stroke="{ACCENT}"/>'
        if line:
            body += code(x, y, line, fill)
        y += 28
    body += (f'<text x="{x}" y="{PY + PH - 50}" class="d" font-size="14">one line per figure;</text>'
             f'<text x="{x}" y="{PY + PH - 28}" class="d" font-size="14">the SVG stays in images/</text>')
    # after: the same slide, figure inlined
    x, y = 433, PY + 40
    lines = [(head[:22], TEXT), ("   " + head[22:], TEXT), ('<div style="display:flex;…">', SUB),
             (svg[0][:20] + " …", LIGHT), ('  viewBox="0 0 1160 600"', LIGHT), ('  width="980" height="507">', LIGHT),
             ("<style>…</style>", SUB), (f"  … {kb:.0f} kB of shapes, text …", MUTED), ("</svg>", LIGHT), ("</div>", SUB)]
    for line, fill in lines:
        body += code(x, y, line, fill)
        y += 26
    body += (f'<text x="{x}" y="{PY + PH - 50}" class="d" font-size="14">the whole SVG, inline:</text>'
             f'<text x="{x}" y="{PY + PH - 28}" class="d" font-size="14">links and hover cards stay live</text>')
    # rendered: a miniature of the hours chart, drawn from the same data
    x0, y0, w0, h0 = 812, PY + 26, 286, 220
    body += (f'<rect x="{x0}" y="{y0}" width="{w0}" height="{h0}" rx="8" fill="{BG}" stroke="{BORDER}"/>'
             f'<text x="{x0 + 12}" y="{y0 + 24}" fill="{TEXT}" font-size="11" font-weight="700">{esc(head[3:30])}…</text>')
    for h in range(1, 5):  # log grid: 1 h to 1,000 h
        gy = y0 + h0 - 20 - h / 4.5 * (h0 - 60)
        body += f'<line x1="{x0 + 14}" y1="{gy:.0f}" x2="{x0 + w0 - 14}" y2="{gy:.0f}" stroke="{BORDER}" stroke-dasharray="2 4"/>'
    for r in (r for r in datasets() if r["hours"]):
        bx = x0 + 20 + (int(r["year"]) - 2011.5) / 13 * (w0 - 40)
        by = y0 + h0 - 20 - (math.log10(float(r["hours"])) + 1) / 4.5 * (h0 - 60)
        body += f'<circle cx="{bx:.0f}" cy="{by:.0f}" r="5" fill="{FAM[r["family"]]}" opacity=".9"/>'
    body += f'<line x1="{x0 + 14}" y1="{y0 + h0 - 14}" x2="{x0 + w0 - 14}" y2="{y0 + h0 - 14}" stroke="{MUTED}"/>'
    body += (f'<text x="808" y="{PY + PH - 50}" class="d" font-size="14">the hours chart, rendered;</text>'
             f'<text x="808" y="{PY + PH - 28}" class="d" font-size="14">hover a dot for its card</text>')
    # the three token sizes build_deck.py knows
    body += f'<text x="40" y="490" class="mu" font-size="13" letter-spacing="1.5">TOKEN SIZES: PICK BY WHAT ELSE IS ON THE SLIDE</text>'
    for k, (tok, size, use) in enumerate((("FIG", "980 × 507", "title + figure"),
                                          ("FIGSM", "860 × 445", "title + figure + a line of text"),
                                          ("FIGFULL", "edge to edge", "figure only, no slide margins"))):
        x = 40 + k * 375
        body += (f'<g class="tk-p" {tip(tok, use)}><rect class="tk-f" x="{x}" y="504" width="330" height="44" rx="10" fill="{CARD}" stroke="{BORDER}"/>'
                 f'<text x="{x + 16}" y="532" {mono} font-size="14" fill="{LIGHT}">&lt;!--{tok}:name--&gt;</text>'
                 f'<text x="{x + 314}" y="532" text-anchor="end" class="d" font-size="14">{size}</text></g>'
                 f'<text x="{x + 4}" y="572" class="d" font-size="14">{use}</text>')
    write("token", css, body)


# ── stack: the repo as layers, sized by tracked files ────────────────────────
def tracked(*prefixes):
    import subprocess
    root = HERE.parents[2]
    try:
        files = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout.split("\n")
    except (OSError, subprocess.CalledProcessError):  # not a git checkout: count what is on disk
        files = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return sum(any(f.startswith(p) for p in prefixes) for f in files)


def fig_stack():
    root = HERE.parents[2]
    skills = sorted(p.parent.name for p in (root / ".agents/skills").glob("*/SKILL.md"))
    decks = sorted(p.parent for p in (root / "decks").glob("*/*/slides.tpl.qmd"))
    cats = sorted({d.parent.name for d in decks})
    layers = [  # name, colour, what it is, paths, prefixes, tip
        ("decks", ACCENT, f"{len(decks)} decks in {len(cats)} categories: {', '.join(cats)}", "decks/<category>/<deck>/",
         ("decks/",), "Markdown source, generated figures and comments, one folder per deck."),
        ("agent skills", PURPLE, f"{len(skills)} skills that build, review and export decks", ".agents/skills/  ·  AGENTS.md",
         (".agents/", "AGENTS.md"), "Skills: " + ", ".join(skills) + ". Any coding agent can follow them."),
        ("fact-checking", YELLOW, "checks a paper deck's claims against the source PDF", "source-review/  ·  scripts/review.sh",
         ("source-review/",), "Ingests review.json (the agent’s claim-by-claim check of a paper deck) and shows each claim next to the page it came from."),
        ("scripts", GREEN, "serve, comment, export to PDF, PPTX and HTML, publish", "scripts/  ·  scripts/pptx_export/",
         ("scripts/", ".github/"), "start.sh runs the live server; export.sh and pptx_export/ write the exports."),
        ("theme", ORANGE, "the agentic look: dark, blue accent, logo, fonts", "themes/agentic.css  ·  assets/",
         ("themes/", "assets/"), "Every deck loads quarto/themes/agentic.css (ported from themes/agentic.css) through its front-matter css: list."),
    ]
    counts = [tracked(*l[4]) for l in layers]
    X, W, Y0, H, GAP = 40, 800, 44, 86, 14
    BX, BW = 880, 230  # file-count bars
    css = ".sk-l{cursor:help}.sk-l:hover rect.sk-f{stroke:#fff}"
    body = f'<rect x="0" y="0" width="1160" height="600" fill="{BG}"/>'
    body += (f'<text x="{X}" y="28" class="mu" font-size="13" letter-spacing="1.5">LAYERS</text>'
             f'<text x="{BX}" y="28" class="mu" font-size="13" letter-spacing="1.5">TRACKED FILES</text>')
    for i, ((name, c, what, paths, _, t), n) in enumerate(zip(layers, counts)):
        y = Y0 + i * (H + GAP)
        inset = i * 14  # each layer a little wider than the one above: a stack
        body += (f'<g class="sk-l" {tip(name, t)}><rect class="sk-f" x="{X + 40 - inset}" y="{y}" width="{W - 80 + 2 * inset}" height="{H}" rx="12" fill="{CARD}" stroke="{c}" stroke-width="2"/>'
                 f'<rect x="{X + 40 - inset}" y="{y}" width="10" height="{H}" rx="5" fill="{c}"/>'
                 f'<text x="{X + 70 - inset}" y="{y + 34}" class="t" font-size="20">{name}</text>'
                 f'<text x="{X + 70 - inset}" y="{y + 62}" class="d" font-size="15">{esc(what)}</text>'
                 f'<text x="{X + W - 60 + inset}" y="{y + 34}" text-anchor="end" class="m" font-size="13">{esc(paths)}</text></g>'
                 f'<rect x="{BX}" y="{y + 30}" width="{BW * n / max(counts):.0f}" height="22" rx="4" fill="{c}" opacity=".75"/>'
                 f'<text x="{BX + BW * n / max(counts) + 8:.0f}" y="{y + 47}" class="t" font-size="16">{n}</text>')
    body += (f'<text x="{X}" y="{Y0 + 5 * (H + GAP) + 6}" class="mu" font-size="13">FOUNDATION</text>'
             f'<text x="{BX}" y="{Y0 + 5 * (H + GAP) + 6}" class="mu" font-size="13">git ls-files, at build time</text>')
    write("stack", css, body)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_map()
    fig_timeline()
    fig_hours()
    fig_diffusion()
    fig_attention()
    fig_pipeline()
    fig_loop()
    fig_intersection()
    fig_licenses()
    fig_lineage()
    fig_architecture()
    fig_deck_types()
    fig_composition()
    fig_images()
    fig_token()
    fig_stack()
