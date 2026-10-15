#!/usr/bin/env python3
"""Minimal generator for a CSS-keyframe-animated deck figure.

Two-phase loop: (1) a dot travels A -> B, (2) B pulses while a second caption
shows. Adapt: extend PHASES, add elements, keep the rn- prefix unique per
figure. Output obeys the build_deck.py contract (exact viewBox, no blank
lines) and keeps base attributes = the static frame for PDF/PPTX.
"""

LOOP = 8.0          # seconds per full loop
PHASES = 2
PW = 100.0 / PHASES  # percent per phase

keyframes, classes = [], []


def vis(name: str, phase: int, a: float = 0.02, b: float = 0.98, fade: float = 0.04):
    """Element with class `name` is visible during [a, b] of `phase` (phase units).

    Phase-0 elements take the starts-visible branch so they show at t=0 and in
    the static frame (PDF/pre-paint) instead of blinking in at every loop wrap.
    """
    s, e, f = (phase + a) * PW, (phase + b) * PW, fade * PW
    if phase == 0 and a <= 0.05:  # starts visible -> valid static frame
        keyframes.append(f"@keyframes {name}{{0%,{e-f:.2f}%{{opacity:1}}{e:.2f}%,100%{{opacity:0}}}}")
    else:
        keyframes.append(f"@keyframes {name}{{0%,{s:.2f}%{{opacity:0}}{s+f:.2f}%,{e-f:.2f}%{{opacity:1}}{e:.2f}%,100%{{opacity:0}}}}")
    classes.append(f".{name}{{animation:{name} {LOOP:g}s linear infinite}}")


def move(name: str, phase: int, waypoints, a: float = 0.05, b: float = 0.8):
    """Group `name` translates through waypoints during its phase, hidden otherwise."""
    s, e = (phase + a) * PW, (phase + b) * PW
    steps = "".join(
        f"{s + (e - s) * i / (len(waypoints) - 1):.2f}%{{transform:translate({dx}px,{dy}px);opacity:1}}"
        for i, (dx, dy) in enumerate(waypoints)
    )
    lx, ly = waypoints[-1]
    keyframes.append(
        f"@keyframes {name}{{0%,{s-0.3:.2f}%{{transform:translate(0,0);opacity:0}}{steps}"
        f"{e+0.3:.2f}%,100%{{transform:translate({lx}px,{ly}px);opacity:0}}}}"
    )
    classes.append(f".{name}{{animation:{name} {LOOP:g}s linear infinite;opacity:0}}")


vis("rn-capA", 0, a=0.0)                            # phase-1 caption (static frame shows it)
vis("rn-capB", 1)                                   # phase-2 caption
vis("rn-pulse", 1, 0.1, 0.9)                        # B highlight during phase 2
move("rn-dot", 0, [(0, 0), (210, -30), (420, 0)])   # dot A -> B along a shallow arc

style = "".join(classes) + "".join(keyframes)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 600" font-family="Inter, sans-serif">
  <rect x="0" y="0" width="1160" height="600" fill="#111111"/>
  <style>{style}</style>
  <rect x="140" y="220" width="240" height="120" rx="14" fill="#1a1a1a" stroke="#3b82f6" stroke-width="2"/>
  <text x="260" y="288" text-anchor="middle" fill="#f0f0f0" font-size="22" font-weight="700">A</text>
  <rect x="780" y="220" width="240" height="120" rx="14" fill="#1a1a1a" stroke="#3fb950" stroke-width="2"/>
  <text x="900" y="288" text-anchor="middle" fill="#f0f0f0" font-size="22" font-weight="700">B</text>
  <rect x="784" y="224" width="232" height="112" rx="12" fill="#3b82f6" opacity="0" class="rn-pulse"/>
  <g class="rn-dot"><circle cx="380" cy="280" r="8" fill="#3b82f6"/></g>
  <rect x="140" y="440" width="880" height="50" rx="10" fill="#1a1a1a" stroke="#666" stroke-width="1.5" stroke-dasharray="6 4"/>
  <text x="580" y="471" text-anchor="middle" fill="#f0f0f0" font-size="15" font-weight="600" opacity="1" class="rn-capA">1 - a payload travels from A to B</text>
  <text x="580" y="471" text-anchor="middle" fill="#f0f0f0" font-size="15" font-weight="600" opacity="0" class="rn-capB">2 - B processes it</text>
</svg>
"""

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "images/example-anim.svg"
    with open(out, "w") as fh:
        fh.write(svg)
    print(f"wrote {out}")
