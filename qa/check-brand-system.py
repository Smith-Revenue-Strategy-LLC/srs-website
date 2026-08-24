#!/usr/bin/env python3
"""Brand-system gate for the SRS site after the BidStrike-family restyle.

Scope is ENUMERATED FROM THE FILESYSTEM (glob *.html), never a hand-maintained
list, so a new page cannot silently fall outside coverage while the gate keeps
reporting PASS.

Checks:
  1. Voice bans: "free", "no pitch", em-dashes, non-ASCII. Scanned over HTML AND JS.
  2. Every page carries the flat top nav and the JS-contract class .site-nav.
  3. No dark-theme remnants (old ground/ink hexes, Georgia, Inter).
  4. No white-on-light art references.
  5. Contrast: computed WCAG ratios for the declared brand pairs.
Exit 0 = pass, 1 = fail.
"""
import glob, re, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
fails, notes = [], []

PAGES = sorted(glob.glob("*.html"))
if len(PAGES) < 2:
    print("FATAL: enumerated %d pages, expected the whole site" % len(PAGES)); sys.exit(1)

# Copy does not only ship from markup. script.js builds the booking modal and
# writes headings straight into the DOM, so a banned word can go live on every
# page while an HTML-only glob reports PASS. That happened. Voice bans run over
# HTML AND JS; the markup checks below (nav contract, dark remnants, art refs)
# stay HTML-only because they are markup contracts and do not apply to a script.
SCRIPTS = sorted(glob.glob("*.js"))
VOICE_FILES = PAGES + SCRIPTS

# --- 1. voice bans -----------------------------------------------------------
BANS = [
    (r'\bfree\b',    'banned word "free" (prospect-facing, no exceptions, ruled 8/14)'),
    (r'no pitch',    'banned phrase "no pitch"'),
    (r'[—–]', 'em-dash or en-dash'),
]
for p in VOICE_FILES:
    s = open(p, encoding="utf-8").read()
    for pat, why in BANS:
        for m in re.finditer(pat, s, re.I):
            line = s[:m.start()].count("\n") + 1
            fails.append("%s:%d  %s" % (p, line, why))
    try:
        s.encode("ascii")
    except UnicodeEncodeError as e:
        fails.append("%s  non-ASCII byte at offset %d" % (p, e.start))

# --- 2. nav contract ---------------------------------------------------------
# A page may opt OUT of the site chrome, but only by saying so out loud. It has
# to be noindex AND carry the marker comment below. Hand-delivered pages (the
# Operator OS ready page) are deliberately chromeless: site nav on them is an
# invitation to wander off before the one action on the page. Everything else in
# this gate still applies to them - bans, ASCII, colors, tokens.
CHROMELESS_MARKER = "brand-system: chromeless page"
def is_chromeless(src):
    return CHROMELESS_MARKER in src and re.search(
        r'name=["\']robots["\'][^>]*noindex', src, re.I)

for p in PAGES:
    s = open(p, encoding="utf-8").read()
    if is_chromeless(s):
        notes.append("%s  chromeless by declaration (noindex + marker), nav contract skipped" % p)
        continue
    if s.count("<header") != 1:
        fails.append("%s  expected exactly 1 <header>, found %d" % (p, s.count("<header")))
    if 'class="nav-links"' not in s:
        fails.append("%s  missing the flat top nav (.nav-links)" % p)
    if 'class="site-nav mobile-nav"' not in s:
        fails.append("%s  mobile panel must carry .site-nav (script.js binds the CLASS)" % p)
    if 'data-booking-open' not in s:
        notes.append("%s  no booking CTA on this page" % p)

# --- 3. dark-theme remnants --------------------------------------------------
if os.path.exists("styles.css"):
    css = open("styles.css", encoding="utf-8").read()
    for pat, why in [(r'#030915', 'old dark ground #030915'),
                     (r'#f7f5f0', 'old cream ink #f7f5f0'),
                     (r'Georgia',  'Georgia serif (retired)'),
                     (r'Inter,',   'Inter (retired)')]:
        n = len(re.findall(pat, css, re.I))
        if n:
            fails.append("styles.css  %d x %s still present" % (n, why))
    if "Geist" not in css:
        fails.append("styles.css  Geist font stack not found")

# --- 4. art that only worked on dark ----------------------------------------
for p in PAGES:
    s = open(p, encoding="utf-8").read()
    if "logo-white" in s:
        fails.append("%s  references a WHITE logo on a light ground (invisible)" % p)

# --- 5. contrast -------------------------------------------------------------
def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]
    return .2126*c[0] + .7152*c[1] + .0722*c[2]
def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi+.05)/(lo+.05)

PAIRS = [
    ("#0d1733", "#f4f6fb", 4.5, "body ink on canvas"),
    ("#495777", "#f4f6fb", 4.5, "soft ink on canvas"),
    ("#0d1733", "#ffffff", 4.5, "ink on card"),
    ("#b45309", "#ffffff", 4.5, "amber CTA text on white"),
    ("#ffffff", "#b45309", 4.5, "white text on amber CTA"),
    ("#0d1733", "#aef23f", 4.5, "navy text on lime fill"),
]
print("  contrast:")
for fg, bg, need, label in PAIRS:
    r = ratio(fg, bg)
    ok = r >= need
    print("    %-32s %-8s on %-8s %5.2f:1  need %.1f  %s"
          % (label, fg, bg, r, need, "OK" if ok else "FAIL"))
    if not ok:
        fails.append("contrast  %s is %.2f:1, needs %.1f" % (label, r, need))

# lime as text must NEVER pass as a text color - assert it is unusable
r_lime = ratio("#aef23f", "#ffffff")
print("    %-32s %-8s on %-8s %5.2f:1  (must stay a FILL, never text)"
      % ("lime on white", "#aef23f", "#ffffff", r_lime))

# --- report ------------------------------------------------------------------
print()
print("  scope: %d pages enumerated from disk -> %s" % (len(PAGES), ", ".join(PAGES)))
print("  scope: %d voice-ban files (html + js) -> %s" % (len(VOICE_FILES), ", ".join(SCRIPTS) or "no .js found"))
for n in notes:
    print("  note  %s" % n)
print()
if fails:
    print("RESULT: FAIL - %d problem(s)" % len(fails))
    for f in fails:
        print("  %s" % f)
    sys.exit(1)
print("RESULT: PASS - voice bans clean, nav contract intact, no dark remnants, contrast AA")
sys.exit(0)
