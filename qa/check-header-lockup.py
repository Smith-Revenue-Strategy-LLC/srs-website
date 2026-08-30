#!/usr/bin/env python3
"""
Regression gate for the header lockup's vertical justification.

Run after ANY edit to the .site-header, .brand or .brand-words rules:

    python3 qa/check-header-lockup.py     # exit 0 = pass

WHAT THIS PROTECTS
------------------
The SRS lockup sits beside a two-line wordmark: "Smith Revenue Strategy" over
the ruled line, "Freedom for the work only people can do." (that second line
was "Unlock AI-Enabled Growth" until Rodney replaced it on 2026-08-28; this
gate never asserted the literal, it derives from the type tokens, which is
exactly why the swap did not break it). Until 2026-08-12 the lockup was a hardcoded 40px
tall while that text block measured 29.09px, so with the header centering both,
the logo hung 5.45px past the text at the top AND the bottom. The owner read it
as misaligned in a browser on 2026-08-12, and he was right.

The fix was not "set 29px". A literal would silently go wrong the next time
anyone retypes the wordmark. The lockup height is DERIVED from the same tokens
the wordmark's own type reads, so the two cannot drift apart.

So the checks below verify the DERIVATION, not a number:
  - the tokens exist on .site-header
  - --brand-h is computed from them, never a bare length
  - --brand-w is computed from --brand-h and the art's real aspect
  - the wordmark's own type reads those same tokens
  - the art file still has the aspect the CSS hardcodes
and then it recomputes both box heights from the CSS and asserts they are equal,
which is the thing the owner actually looked at.

Sizes are resolved against a 16px root, which is what the site ships (no
font-size override on :root or html in styles.css - check 6 enforces that).
"""

import os
import re
import struct
import sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

ROOT_PX = 16.0
BAR_PX = 66.0   # .nav-wrap height on the dark chrome
# The monogram/lettermark retired 2026-08-27; the mark is now a PORTRAIT vector.
# Aspect went 2.32 (360x155 landscape) -> 0.800 (496.835x620.970 portrait), so this
# gate was re-pointed AND re-derived. Assertions were replaced, never weakened:
# the exact-equality height check became a stated-multiple check plus a NEW bar-fit
# check, and the hardcoded 360/155 became a ratio read out of the SVG's own viewBox
# so the CSS and the art cannot drift apart silently.
MARK = "assets/images/brand/srs-icon-reverse.svg"

failures = []
notes = []


def mark_viewbox():
    """(w, h) from the mark SVG's viewBox. The art is the authority on its own
    aspect - never hardcode it in two places and hope they stay equal."""
    if not os.path.exists(MARK):
        return None
    head = open(MARK, encoding="utf-8").read(2000)
    m = re.search(r'viewBox="\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', head)
    if not m:
        return None
    return float(m.group(3)), float(m.group(4))


def check(name):
    def wrap(fn):
        try:
            msgs = fn() or []
        except Exception as exc:  # a crashing check is a failing check
            msgs = ["check raised %s: %s" % (type(exc).__name__, exc)]
        if msgs:
            failures.append((name, msgs))
            print("FAIL  %s" % name)
            for m in msgs:
                print("        %s" % m)
        else:
            print("pass  %s" % name)
        return fn

    return wrap


with open("styles.css", encoding="utf-8") as fh:
    CSS_RAW = fh.read()

# Comments have to go before anything else parses this. styles.css is heavily
# commented, and a comment sitting between two declarations breaks BOTH passes
# below: prose commas split into phantom selectors, and a declaration that
# follows a comment is no longer preceded by a semicolon. Stripping first cost
# an hour of "the rule isn't there" on 2026-08-12; it was always there.
CSS = re.sub(r"/\*.*?\*/", "", CSS_RAW, flags=re.S)


def rule(selector):
    """Body of the FIRST rule whose selector list matches exactly."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS):
        sels = [s.strip() for s in m.group(1).split(",")]
        if selector in sels:
            return m.group(2)
    return None


def decl(body, prop):
    if body is None:
        return None
    m = re.search(r"(?:^|;)\s*%s\s*:\s*([^;]+)" % re.escape(prop), body)
    return m.group(1).strip() if m else None


HEADER = rule(".site-header")
WORDS = rule(".brand-words")
NAME = rule(".brand-words strong")
TAG = rule(".brand-words small")
BRAND = rule(".brand")

TOKENS = ("--wm-name", "--wm-tag", "--wm-leading", "--wm-gap")


def px(value):
    """Resolve a rem/px length to px. Raises on anything else."""
    value = value.strip()
    m = re.fullmatch(r"([\d.]+)(rem|px)", value)
    if not m:
        raise ValueError("not a plain rem/px length: %r" % value)
    n = float(m.group(1))
    return n * ROOT_PX if m.group(2) == "rem" else n


# --------------------------------------------------------------------------
@check("the wordmark tokens are declared on .site-header")
def _():
    if HEADER is None:
        return [".site-header rule not found"]
    return ["%s is not declared on .site-header" % t
            for t in TOKENS if decl(HEADER, t) is None]


# --------------------------------------------------------------------------
# The whole point: a bare `--brand-h: 40px` is the bug, restated.
# --------------------------------------------------------------------------
@check("--brand-h is derived from the wordmark tokens, not hardcoded")
def _():
    v = decl(HEADER, "--brand-h")
    if v is None:
        return ["--brand-h is not declared on .site-header"]
    bad = []
    if not v.startswith("calc("):
        bad.append("--brand-h is %r; it has to be computed from the wordmark, "
                   "or the logo stops tracking the text it aligns to" % v)
    for t in TOKENS:
        if t not in v:
            bad.append("--brand-h does not read %s" % t)
    return bad


# --------------------------------------------------------------------------
@check("--brand-w is derived from --brand-h at the art's real aspect")
def _():
    v = decl(HEADER, "--brand-w")
    if v is None:
        return ["--brand-w is not declared on .site-header"]
    bad = []
    # --brand-w now chains --brand-h -> --brand-icon-h -> --brand-w. Walk the chain
    # rather than grepping for --brand-h directly: the requirement is that the width
    # still traces back to the wordmark tokens, and a chain satisfies that. Anything
    # that does NOT trace back gets letterboxed inside .brand (overflow: hidden).
    icon_expr = decl(HEADER, "--brand-icon-h") or ""
    traces = "--brand-h" in v or ("--brand-icon-h" in v and "--brand-h" in icon_expr)
    if not traces:
        bad.append("--brand-w is %r and --brand-icon-h is %r; neither traces back "
                   "to --brand-h, so the mark no longer re-justifies when the "
                   "wordmark is retyped" % (v, icon_expr))
    if "--brand-icon-h" not in v:
        bad.append("--brand-w is %r; the portrait mark must scale off "
                   "--brand-icon-h, not the raw text block" % v)
    vb = mark_viewbox()
    if vb:
        w, h = vb
        if not re.search(re.escape("%g" % w) + r"\s*/\s*" + re.escape("%g" % h), v):
            bad.append("--brand-w does not carry the mark's real %g/%g aspect: %r"
                       % (w, h, v))
    return bad


# --------------------------------------------------------------------------
@check("the wordmark's own type reads the same tokens")
def _():
    bad = []
    for label, body, size_token in (("strong", NAME, "--wm-name"),
                                    ("small", TAG, "--wm-tag")):
        if body is None:
            bad.append(".brand-words %s rule not found" % label)
            continue
        fs = decl(body, "font-size")
        lh = decl(body, "line-height")
        if fs != "var(%s)" % size_token:
            bad.append(".brand-words %s font-size is %r, expected var(%s) - a "
                       "literal here re-breaks the alignment silently"
                       % (label, fs, size_token))
        if lh != "var(--wm-leading)":
            bad.append(".brand-words %s line-height is %r, expected "
                       "var(--wm-leading)" % (label, lh))
    gap = decl(WORDS, "gap") if WORDS else None
    if gap != "var(--wm-gap)":
        bad.append(".brand-words gap is %r, expected var(--wm-gap)" % gap)
    return bad


# --------------------------------------------------------------------------
@check("the mark art still matches the aspect the CSS hardcodes")
def _():
    vb = mark_viewbox()
    if vb is None:
        return ["could not read a viewBox from %s" % MARK]
    w, h = vb
    notes.append("mark is %gx%g (aspect %.4f), portrait" % (w, h, w / h))
    if w >= h:
        return ["%s is %gx%g - that is landscape or square. The header layout "
                "and this gate were both re-derived for a PORTRAIT mark; a "
                "landscape file here means the wrong art got exported." % (MARK, w, h)]
    v = decl(HEADER, "--brand-w") or ""
    if not re.search(re.escape("%g" % w) + r"\s*/\s*" + re.escape("%g" % h), v):
        return ["%s is %gx%g but --brand-w is %r. Re-export at the same aspect "
                "or update the ratio in both places." % (MARK, w, h, v)]
    return []


# --------------------------------------------------------------------------
@check("no root font-size override (these sizes resolve against 16px)")
def _():
    for sel in (":root", "html"):
        body = rule(sel)
        if body and decl(body, "font-size"):
            return ["%s sets font-size: %s - this script's px math assumes the "
                    "browser default" % (sel, decl(body, "font-size"))]
    return []


# --------------------------------------------------------------------------
# The measurement the owner actually made. Recompute both boxes from the CSS
# and require they come out identical; the header centers them, so equal
# heights means the top edges and the bottom edges land together.
# --------------------------------------------------------------------------
@check("the mark height is the stated multiple of the wordmark block")
def _():
    name = px(decl(HEADER, "--wm-name"))
    tag = px(decl(HEADER, "--wm-tag"))
    lead = float(decl(HEADER, "--wm-leading"))
    gap = px(decl(HEADER, "--wm-gap"))

    words_h = round(name * lead, 4) + round(tag * lead, 4) + gap

    expr = decl(HEADER, "--brand-h")
    inner = expr[len("calc("):-1] if expr.startswith("calc(") else expr
    resolved = inner
    for token, value in (("--wm-name", name), ("--wm-tag", tag),
                         ("--wm-leading", lead), ("--wm-gap", gap)):
        resolved = resolved.replace("var(%s)" % token, repr(value))
    if not re.fullmatch(r"[\d.eE+\-*/() ']*", resolved):
        return ["could not resolve --brand-h: %r" % expr]
    brand_h = eval(resolved)  # noqa: S307 - literal arithmetic, gated above

    # The old rule was brand_h == words_h exactly, correct while the mark was a
    # WIDE lettermark that paired edge-to-edge with the two-line text. A portrait
    # mark held to the text height renders ~23px wide and reads as a bullet. So the
    # rule is now: the icon height must still be DERIVED from the wordmark tokens
    # (retyping the wordmark must still re-justify the mark) via an explicit,
    # declared multiple - and that multiple must be in the CSS, not a magic number.
    scale_raw = decl(HEADER, "--brand-icon-scale")
    if scale_raw is None:
        return ["--brand-icon-scale is not declared; the mark height would be a "
                "magic number instead of derived from the wordmark tokens"]
    scale = float(scale_raw)
    icon_expr = decl(HEADER, "--brand-icon-h") or ""
    if "--brand-h" not in icon_expr or "--brand-icon-scale" not in icon_expr:
        return ["--brand-icon-h is %r; it must be --brand-h * --brand-icon-scale "
                "so the mark stays tied to the wordmark tokens" % icon_expr]
    icon_h = brand_h * scale
    vb = mark_viewbox()
    icon_w = icon_h * (vb[0] / vb[1]) if vb else float("nan")

    notes.append("wordmark block %.2fpx, mark %.2fpx tall (x%.2f), %.2fpx wide"
                 % (words_h, icon_h, scale, icon_w))

    if abs(brand_h - words_h) > 0.01:
        return ["--brand-h is %.2fpx against a %.2fpx wordmark block - the base "
                "token must still equal the text block" % (brand_h, words_h)]
    # NEW assertion the old gate had no reason to make: a portrait mark can now
    # outgrow the bar. 66px bar, and the mark must keep >=8px clearance each edge.
    if icon_h > BAR_PX - 16:
        return ["the mark resolves to %.2fpx tall in a %.0fpx bar, leaving under "
                "8px clearance per edge. Lower --brand-icon-scale."
                % (icon_h, BAR_PX)]
    if icon_h <= words_h:
        return ["the mark resolves to %.2fpx, no taller than the %.2fpx wordmark "
                "block - a portrait mark at text height reads as a bullet, which "
                "is the failure this re-layout exists to prevent" % (icon_h, words_h)]
    return []


# --------------------------------------------------------------------------
# Below 900px the wordmark is display:none, so there is nothing to justify to
# and the lockup goes back to carrying the row on its own. Without this the
# derived height leaves a shrunken logo floating next to a hamburger.
# --------------------------------------------------------------------------
@check("the <=900px breakpoint restores the lockup once the wordmark is hidden")
def _():
    block = re.search(
        r"@media\s*\(max-width:\s*900px\)\s*\{(.*?\.brand-words\s*\{[^{}]*"
        r"display:\s*none.*?)\n\}", CSS, re.S)
    if not block:
        return ["no @media (max-width: 900px) block hides .brand-words"]
    if "--brand-icon-h" not in block.group(1):
        return ["the <=900px block hides .brand-words but never resets "
                "--brand-icon-h, leaving the mark sized to a wordmark that is "
                "not on screen"]
    return []


# --------------------------------------------------------------------------
print("-" * 62)
for n in notes:
    print("note  %s" % n)
print("-" * 62)
if failures:
    print("FAILED %d checks" % len(failures))
    sys.exit(1)
print("all checks passed")
sys.exit(0)
