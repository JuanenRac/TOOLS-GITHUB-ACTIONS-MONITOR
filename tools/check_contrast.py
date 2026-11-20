#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_contrast.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The contrast gate: a failing pair of colours is a failing build, not an opinion.

    python tools/check_contrast.py            # prints every problem and exits 1 when there is one
    python tools/check_contrast.py --list     # prints every theme with its worst pair

What is measured, from the real palettes of the page (assets/static/actions_monitor.html and the sixteen themes it carries, which the wall screens use too):
  * text on every surface: --text and --mut on --bg, --panel and --panel2 reach 4.5:1 (WCAG AA for normal text);
  * the colour of a state (--ok, --bad, --warn, --run) on --panel reaches 3:1 (WCAG AA for graphics), in every theme and in the colour-blind palette of both modes;
  * the text on a coloured fill (--on on --acc) reaches 4.5:1;
  * the colour-blind palette keeps the four states apart for the three common kinds of colour blindness (they are simulated with the matrices of Machado et al. and the distance in CIELAB stays above
    MIN_DELTA_E);
  * a rule of style: text is never dimmed with `opacity` (a dimmed text drops under 4.5:1 without any colour changing); the declarations that do it today are counted and may not grow (OPACITY_BASELINE).
Nothing here needs a browser: it reads the colours the page declares.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "monitor"
PAGE = MON / "assets" / "static" / "actions_monitor.html"
TEXT_MIN, GRAPHIC_MIN = 4.5, 3.0
MIN_DELTA_E = 18.0
OPACITY_BASELINE = 11      # declarations of the page that set an opacity under 1 (disabled and muted rows, a stale figure); a new one fails the gate (lower this number when one is removed)
STATES = ("ok", "bad", "warn", "run")
CVD = {      # Machado, Oliveira, Fernandes (2009), severity 1.0, on linear RGB
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}
VAR = re.compile(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\b")


def _rgb(color):
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color):
    r, g, b = (_linear(c) for c in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _lab(linear):
    r, g, b = linear
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x / 0.95047), f(y), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def simulate(color, kind):
    """The colour as a person with that kind of colour blindness sees it, as CIELAB."""
    linear = [_linear(c) for c in _rgb(color)]
    matrix = CVD[kind]
    mixed = [max(0.0, min(1.0, sum(m * v for m, v in zip(row, linear)))) for row in matrix]
    return _lab(mixed)


def delta_e(a, b, kind):
    la, lb = simulate(a, kind), simulate(b, kind)
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


def page_text():
    return PAGE.read_text(encoding="utf-8")


def themes(text=None):
    """{name: {variable: colour}} of every palette the page ships: dark and light, the sixteen themes and the colour-blind palette of both modes."""
    text = text or page_text()
    sys.path.insert(0, str(MON / "src"))
    from github_actions_monitor.app import screens
    base = dict(VAR.findall(re.search(r"^:root\{([^}]*)\}", text, re.M).group(1)))
    out = {"dark": dict(base)}
    out["light"] = {**base, **dict(VAR.findall(re.search(r":root\[data-theme=light\]\{([^}]*)\}", text).group(1)))}
    for name, body in re.findall(r':root\[data-theme="([^"]+)"\]\{([^{}]*)\}', screens.theme_css()):
        out[name] = {**base, **dict(VAR.findall(body))}
    blind = re.search(r":root\[data-palette=colorblind\]\{([^}]*)\}", text)
    blind_light = re.search(r":root\[data-palette=colorblind\]\[data-theme=light\]\{([^}]*)\}", text)
    if blind:
        out["colorblind (dark)"] = {**base, **dict(VAR.findall(blind.group(1)))}
    if blind and blind_light:
        out["colorblind (light)"] = {**out["light"], **dict(VAR.findall(blind.group(1))), **dict(VAR.findall(blind_light.group(1)))}
    return out


def problems(text=None):
    found = []
    for name, v in themes(text).items():
        for fg in ("text", "mut"):
            for bg in ("bg", "panel", "panel2"):
                if fg in v and bg in v and ratio(v[fg], v[bg]) < TEXT_MIN:
                    found.append(f"{name}: --{fg} on --{bg} is {ratio(v[fg], v[bg]):.2f}:1, under {TEXT_MIN}:1")
        for state in STATES:
            if state in v and "panel" in v and ratio(v[state], v["panel"]) < GRAPHIC_MIN:
                found.append(f"{name}: --{state} on --panel is {ratio(v[state], v['panel']):.2f}:1, under {GRAPHIC_MIN}:1")
        if "on" in v and "acc" in v and ratio(v["on"], v["acc"]) < TEXT_MIN:
            found.append(f"{name}: --on on --acc is {ratio(v['on'], v['acc']):.2f}:1, under {TEXT_MIN}:1")
        if name.startswith("colorblind"):
            for kind in CVD:
                for i, a in enumerate(STATES):
                    for b in STATES[i + 1:]:
                        if delta_e(v[a], v[b], kind) < MIN_DELTA_E:
                            found.append(f"{name}: {a} and {b} look alike for {kind} (distance {delta_e(v[a], v[b], kind):.1f})")
    return found


def opacity_rules(text=None):
    """How many declarations of the style dim something with `opacity` (a number under 1): the count must not grow."""
    text = text or page_text()
    css = text[text.index("<style>"):text.index("</style>")]
    return len(re.findall(r"opacity:\s*0?\.\d+", css))


def main(argv):
    if "--list" in argv:
        for name, v in themes().items():
            worst = min(ratio(v[fg], v[bg]) for fg in ("text", "mut") for bg in ("bg", "panel", "panel2") if fg in v and bg in v)
            print(f"{name}: worst text pair {worst:.2f}:1")
        return 0
    found = problems()
    if opacity_rules() > OPACITY_BASELINE:
        found.append(f"{opacity_rules()} rules dim something with opacity, more than the {OPACITY_BASELINE} of the baseline: use a colour of its own that reaches {TEXT_MIN}:1")
    for line in found:
        print("CONTRAST=FAIL " + line)
    print("CONTRAST=PASS" if not found else f"CONTRAST=FAIL {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
