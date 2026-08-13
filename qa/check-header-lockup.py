#!/usr/bin/env python3
"""
Regression gate for the header lockup's vertical justification.

Run after ANY edit to the .site-header, .brand or .brand-words rules:

    python3 qa/check-header-lockup.py     # exit 0 = pass

WHAT THIS PROTECTS
------------------
The SRS lockup sits beside a two-line wordmark: "Smith Revenue Strategy" over
"Unlock AI-Enabled Growth". Until 2026-08-12 the lockup was a hardcoded 40px
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
LETTERMARK = "assets/images/brand/srs-lettermark.png"

failures = []
notes = []


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
    if "--brand-h" not in v:
        bad.append("--brand-w is %r; it has to scale with --brand-h or the "
                   "lockup gets letterboxed inside .brand (overflow: hidden)" % v)
    if not re.search(r"360\s*/\s*155", v):
        bad.append("--brand-w does not carry the 360/155 aspect: %r" % v)
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
@check("srs-lettermark.png still matches the aspect the CSS hardcodes")
def _():
    if not os.path.exists(LETTERMARK):
        return ["missing asset %s" % LETTERMARK]
    with open(LETTERMARK, "rb") as fh:
        head = fh.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return ["%s is not a PNG" % LETTERMARK]
    w, h = struct.unpack(">II", head[16:24])
    notes.append("lettermark is %dx%d (aspect %.4f)" % (w, h, w / h))
    if (w, h) != (360, 155):
        return ["%s is %dx%d; --brand-w hardcodes 360/155. Re-export at the "
                "same aspect or update the ratio in both places."
                % (LETTERMARK, w, h)]
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
@check("lockup height equals the wordmark block height (top and bottom flush)")
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

    notes.append("wordmark block %.2fpx, lockup %.2fpx, overhang %.2fpx/edge"
                 % (words_h, brand_h, (brand_h - words_h) / 2))
    notes.append("lockup renders %.2fpx wide" % (brand_h * 360 / 155))

    if abs(brand_h - words_h) > 0.01:
        return ["lockup is %.2fpx tall against a %.2fpx wordmark, so it hangs "
                "%.2fpx past the text at each edge"
                % (brand_h, words_h, abs(brand_h - words_h) / 2)]
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
    if "--brand-h" not in block.group(1):
        return ["the <=900px block hides .brand-words but never resets "
                "--brand-h, leaving the lockup sized to a wordmark that is "
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
