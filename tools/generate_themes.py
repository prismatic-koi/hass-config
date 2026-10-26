#!/usr/bin/env python3
"""Generate Home Assistant themes from the nixos-config colour schemes.

Usage: tools/generate_themes.py <path-to-nixos-config-checkout>

The theme names match the `nx.desktop.theme` values in nixos-config, so a
browser can set `selectedTheme` in localStorage to the system theme name.
"""

import json
import subprocess
import sys
from pathlib import Path

import ha_semantic_map

THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"

# Keep in sync with byTheme in modules/colour-scheme/default.nix.
NIX_EXPR = """
let
  colourLib = import ./lib.nix;
  mk = n: import (./palettes + "/${n}.nix") { inherit colourLib; };
  everforest = mk "everforest";
  gruvbox = mk "gruvbox";
in [
  (mk "catppuccin-latte")
  (mk "catppuccin-mocha")
  (mk "edge")
  everforest.dark
  everforest.light
  (mk "github-light")
  (mk "nightcity-kabuki")
  (mk "onedark")
  gruvbox.light
  gruvbox.dark
]
"""


def parse(c):
    c = c.lstrip("#")
    return [int(c[i : i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, pct):
    """Interpolate pct percent of the way from a to b."""
    ca, cb = parse(a), parse(b)
    return "#" + "".join(
        f"{round(x + (y - x) * pct / 100):02x}" for x, y in zip(ca, cb)
    )


def ramp(colour, anchor, low, high):
    """Build an HA core colour ramp (05..95) with `colour` at step `anchor`.

    Steps below the anchor move toward `low`, steps above move toward `high`.
    The end steps stop short of the end colours so they keep some hue.
    """
    steps = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
    out = {}
    for s in steps:
        if s < anchor:
            c = mix(colour, low, (anchor - s) / anchor * 90)
        elif s > anchor:
            c = mix(colour, high, (s - anchor) / (100 - anchor) * 90)
        else:
            c = colour
        out[f"{s:02d}"] = c
    return out


def build(t):
    n, h, br, r = t["neutrals"], t["hues"], t["brights"], t["roles"]
    dark = t["type"] == "dark"
    bg, fg, fg_dim = n["background_0"], n["foreground"], n["foreground_dim"]

    # HA puts cards on top of a page background. Some schemes set
    # background_dim equal to background_0, so step one shade along the ramp
    # to keep cards distinct from the page.
    if n["background_dim"] != bg:
        page, card, secondary = n["background_dim"], bg, n["background_1"]
    elif dark:
        page, card, secondary = bg, n["background_1"], n["background_2"]
    else:
        page, card, secondary = n["background_1"], bg, n["background_2"]

    low, high = (page, "#ffffff") if dark else ("#000000", bg)
    v = {}

    # Text
    v["primary-text-color"] = fg
    v["secondary-text-color"] = fg_dim
    v["disabled-text-color"] = mix(fg_dim, page, 40)
    v["text-primary-color"] = card
    v["text-light-primary-color"] = fg
    v["text-accent-color"] = card

    # Main interface
    v["primary-color"] = r["primary"]
    v["dark-primary-color"] = mix(r["primary"], low, 20)
    v["darker-primary-color"] = mix(r["primary"], low, 40)
    v["light-primary-color"] = mix(r["primary"], card, 50)
    v["accent-color"] = r["secondary"]
    v["divider-color"] = mix(card, fg, 12)
    v["outline-color"] = mix(card, fg, 12)
    v["outline-hover-color"] = mix(card, fg, 24)
    v["scrollbar-thumb-color"] = n["background_3"]
    v["error-color"] = r["error"]
    v["warning-color"] = r["warning"]
    v["success-color"] = r["success"]
    v["info-color"] = r["info"]

    # Backgrounds
    v["primary-background-color"] = page
    v["clear-background-color"] = page
    v["card-background-color"] = card
    v["secondary-background-color"] = secondary
    v["markdown-code-background-color"] = page

    # Header and sidebar
    v["app-header-background-color"] = card
    v["app-header-text-color"] = fg
    v["sidebar-background-color"] = card
    v["sidebar-text-color"] = fg
    v["sidebar-icon-color"] = fg_dim
    v["sidebar-selected-text-color"] = r["primary"]
    v["sidebar-selected-icon-color"] = r["primary"]
    v["sidebar-selected-background-color"] = secondary

    # Inputs
    v["input-fill-color"] = secondary
    v["input-disabled-fill-color"] = page
    v["input-ink-color"] = fg
    v["input-label-ink-color"] = fg_dim
    v["input-disabled-ink-color"] = v["disabled-text-color"]
    v["input-dropdown-icon-color"] = fg_dim
    v["input-idle-line-color"] = n["background_4"]
    v["input-hover-line-color"] = fg
    v["input-disabled-line-color"] = n["background_2"]
    v["input-outlined-idle-border-color"] = n["background_4"]
    v["input-outlined-hover-border-color"] = fg
    v["input-outlined-disabled-border-color"] = n["background_2"]

    # Named colours. HA derives every state, weather and badge colour from
    # these, so mapping them recolours the dashboards.
    v["red-color"] = h["red"]
    v["pink-color"] = h["pink"]
    v["purple-color"] = h["purple"]
    v["deep-purple-color"] = h["violet"]
    v["indigo-color"] = h["indigo"]
    v["blue-color"] = h["blue"]
    v["light-blue-color"] = h["sky"]
    v["cyan-color"] = h["cyan"]
    v["teal-color"] = h["teal"]
    v["green-color"] = h["green"]
    v["light-green-color"] = mix(h["green"], h["lime"], 50)
    v["lime-color"] = h["lime"]
    v["yellow-color"] = h["yellow"]
    v["amber-color"] = h["amber"]
    v["orange-color"] = h["orange"]
    v["deep-orange-color"] = mix(h["orange"], h["red"], 50)
    v["brown-color"] = h["brown"]
    v["light-grey-color"] = mix(fg_dim, fg, 50)
    v["grey-color"] = fg_dim
    v["dark-grey-color"] = n["background_5"]
    v["blue-grey-color"] = mix(h["blue"], fg_dim, 60)
    v["disabled-color"] = n["background_3"]

    # State colours
    v["state-icon-color"] = r["primary"]
    v["state-active-color"] = h["amber"]
    v["state-inactive-color"] = fg_dim
    v["state-weather-snowy-color"] = mix(h["sky"], "#ffffff", 50)

    # Energy dashboard
    v["energy-grid-consumption-color"] = h["blue"]
    v["energy-grid-return-color"] = h["purple"]
    v["energy-solar-color"] = h["orange"]
    v["energy-non-fossil-color"] = h["green"]
    v["energy-battery-out-color"] = h["teal"]
    v["energy-battery-in-color"] = h["pink"]
    v["energy-gas-color"] = mix(h["red"], low, 30)
    v["energy-water-color"] = h["cyan"]

    # Graph series colours. The order follows the HA default palette.
    series = ["blue", "yellow", "red", "emerald", "purple", "pink", "brown", "sky", "green"]
    tiers = [
        lambda c: c,
        lambda c: mix(c, low, 30),
        lambda c: mix(c, high, 30),
        lambda c: mix(c, low, 50),
        lambda c: mix(c, high, 50),
        lambda c: mix(c, fg_dim, 40),
    ]
    for i in range(54):
        v[f"color-{i + 1}"] = tiers[i // len(series)](h[series[i % len(series)]])

    # Code editor
    v["codemirror-keyword"] = h["fuchsia"]
    v["codemirror-operator"] = h["cyan"]
    v["codemirror-variable"] = h["red"]
    v["codemirror-variable-2"] = fg
    v["codemirror-variable-3"] = h["yellow"]
    v["codemirror-builtin"] = h["yellow"]
    v["codemirror-atom"] = h["orange"]
    v["codemirror-number"] = h["orange"]
    v["codemirror-def"] = h["blue"]
    v["codemirror-string"] = h["green"]
    v["codemirror-string-2"] = h["red"]
    v["codemirror-comment"] = fg_dim
    v["codemirror-tag"] = h["red"]
    v["codemirror-meta"] = h["yellow"]
    v["codemirror-attribute"] = h["fuchsia"]
    v["codemirror-property"] = h["blue"]
    v["codemirror-qualifier"] = h["yellow"]
    v["codemirror-type"] = h["yellow"]

    # HA design-system ramps. HA only generates the primary ramp for the
    # built-in default theme, so a custom theme must set every step. Without
    # them, buttons and form fills keep the HA blue and grey.
    ramps = {}
    for name, colour, anchor in [
        ("primary", r["primary"], 40),
        ("red", r["error"], 50),
        ("orange", r["warning"], 60),
        ("green", r["success"], 60),
    ]:
        ramps[name] = ramp(colour, anchor, low, high)
        for step, c in ramps[name].items():
            v[f"ha-color-{name}-{step}"] = c

    if dark:
        neutral = [
            page, bg, n["background_1"], n["background_2"], n["background_3"],
            n["background_5"], mix(n["background_5"], fg_dim, 50), fg_dim,
            mix(fg_dim, fg, 50), fg, mix(fg, "#ffffff", 50),
        ]
    else:
        neutral = [
            mix(fg, "#000000", 50), mix(fg, "#000000", 25), fg,
            mix(fg_dim, fg, 50), fg_dim, mix(n["background_5"], fg_dim, 50),
            n["background_5"], n["background_4"], n["background_3"],
            n["background_2"], n["background_1"],
        ]
    ramps["neutral"] = dict(
        zip(["05", "10", "20", "30", "40", "50", "60", "70", "80", "90", "95"], neutral)
    )
    for step, c in ramps["neutral"].items():
        v[f"ha-color-neutral-{step}"] = c

    families = {
        "primary": "primary", "neutral": "neutral", "disabled": "neutral",
        "danger": "red", "warning": "orange", "success": "green",
    }
    semantic = dict(ha_semantic_map.LIGHT)
    if dark:
        semantic.update(ha_semantic_map.DARK)
    for token, step in semantic.items():
        family = token.split("-")[1]
        if step == "loud-text":
            c = card
        elif family == "surface":
            c = ramps["neutral"][step]
        else:
            c = ramps[families[family]][step]
        v[f"ha-color-{token}"] = c

    v["ha-color-text-primary"] = fg
    v["ha-color-text-secondary"] = fg_dim
    v["ha-color-text-disabled"] = v["disabled-text-color"]
    v["ha-color-text-link"] = r["primary"]
    v["ha-color-surface-default"] = card
    v["ha-color-surface-low"] = page
    v["ha-color-surface-lower"] = mix(page, low, 30)
    v["ha-color-on-surface-default"] = fg
    v["ha-color-on-primary-loud"] = card
    v["ha-color-on-danger-loud"] = card
    v["ha-color-on-warning-loud"] = card
    v["ha-color-on-success-loud"] = card
    v["ha-color-on-neutral-loud"] = card
    v["ha-color-form-background"] = secondary
    v["ha-color-form-background-hover"] = n["background_2"]
    v["ha-color-form-background-disabled"] = page
    v["ha-color-focus"] = r["secondary"]

    # Switches. HA reads only the ha-switch-* variables. The thumb must
    # contrast with the unchecked track, or the off state is invisible.
    track = n["background_2"] if dark else n["background_4"]
    v["ha-switch-checked-background-color"] = v["light-primary-color"]
    v["ha-switch-checked-border-color"] = v["light-primary-color"]
    v["ha-switch-checked-thumb-background-color"] = r["primary"]
    v["ha-switch-checked-thumb-border-color"] = r["primary"]
    v["ha-switch-background-color"] = track
    v["ha-switch-border-color"] = track
    v["ha-switch-thumb-background-color"] = fg_dim
    v["ha-switch-thumb-border-color"] = fg_dim

    # HACS
    v["hacs-status-installed"] = r["success"]
    v["hacs-status-not-loaded"] = r["error"]
    v["hacs-status-pending-update"] = r["warning"]

    return v


def render(t, rev):
    mode = t["type"]
    lines = [
        f"# Generated by tools/generate_themes.py from prismatic-koi/nixos-config@{rev}.",
        "# Do not edit by hand. Run the generator again.",
        f"{t['name']}:",
        "  modes:",
        f"    {mode}:",
    ]
    lines += [f'      {k}: "{val}"' for k, val in build(t).items()]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    repo = Path(sys.argv[1]).resolve()
    scheme_dir = repo / "modules" / "colour-scheme"
    palettes = json.loads(
        subprocess.run(
            ["nix-instantiate", "--eval", "--strict", "--json", "-E", NIX_EXPR],
            cwd=scheme_dir, check=True, capture_output=True, text=True,
        ).stdout
    )
    rev = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    for old in THEMES_DIR.glob("*.yaml"):
        old.unlink()
    for t in palettes:
        (THEMES_DIR / f"{t['name']}.yaml").write_text(render(t, rev))
        print(f"wrote themes/{t['name']}.yaml")


if __name__ == "__main__":
    main()
