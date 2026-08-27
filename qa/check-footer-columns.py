#!/usr/bin/env python3
"""Gate for the five-column footer and the operating-principles band.

SCOPE ENUMERATED FROM THE FILESYSTEM. Same reasoning as check-nav-dropdown.py: the
8/24 draft hardcoded an "Operator OS" link into the Solutions column, but that page
is Tier 2 and does not exist, so the gate would have demanded a footer link to a
404. Internal destinations are therefore checked against what is actually on disk.

Run: python3 qa/check-footer-columns.py   # exit 0 = pass
"""
import glob, sys, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

CHROMELESS = "brand-system: chromeless page"
PAGES = [p for p in sorted(glob.glob("*.html"))
         if CHROMELESS not in open(p, encoding="utf-8").read()]

COLS = ["Solutions", "Resources", "Company", "Legal"]
# The authoritative wording, confirmed by Rodney 2026-07-23. The five
# reverse-engineered "Brand values" were DELETED from srs-brand-voice.md on
# 2026-08-18 and must never come back - two layers remain, purpose and these three.
PRINCIPLES = ["Full Disclosure", "Congruence", "Excellent Service"]
BANNED_VALUES = ["Brand values", "Brand Values"]

# Internal hrefs the footer may offer, gated on the page existing.
CANDIDATES = {"/construction": "construction.html",
              "/operator-os":  "operator-os.html",
              "/results":      "results.html",
              "/events":       "events.html",
              "/faq":          "faq.html",
              "/about":        "about.html",
              "/is-this-you":  "is-this-you.html",
              "/contact":      "contact.html",
              "/privacy":      "privacy.html"}

fails = []
foot_re = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)
band_re = re.compile(r'<section class="principles-band".*?</section>', re.S)
seen_band = {}

for p in PAGES:
    s = open(p, encoding="utf-8").read()
    m = foot_re.search(s)
    if not m:
        fails.append("%s  no site-footer" % p)
        continue
    foot = m.group(0)

    if 'class="foot-top"' not in foot:
        fails.append("%s  missing .foot-top" % p)
    if 'class="foot-bottom"' not in foot:
        fails.append("%s  missing .foot-bottom" % p)
    if 'class="bs-footer-block"' not in foot:
        fails.append("%s  bs-footer-block dropped - check-bidstrike-surfaces.py "
                     "requires it on every chrome page" % p)
    for c in COLS:
        if ">%s<" % c not in foot:
            fails.append("%s  footer missing column -> %s" % (p, c))

    # no footer link may point at a page that does not exist
    for href in re.findall(r'href="(/[^"#?]*)"', foot):
        if href in CANDIDATES and not os.path.exists(CANDIDATES[href]):
            fails.append("%s  footer links %s but %s does not exist"
                         % (p, href, CANDIDATES[href]))

    b = band_re.search(s)
    if not b:
        fails.append("%s  missing .principles-band" % p)
    else:
        seen_band.setdefault(b.group(0), []).append(p)
        for pr in PRINCIPLES:
            if pr not in b.group(0):
                fails.append("%s  principles band missing -> %s" % (p, pr))
    for bv in BANNED_VALUES:
        if bv in s:
            fails.append('%s  the deleted "%s" layer is back - only purpose and '
                         "the three principles survive (ruled 8/18)" % (p, bv))

# the band is site-wide chrome, so it drifts the same way the footer does
if len(seen_band) > 1:
    fails.append("principles band differs between pages: %s"
                 % [v for v in seen_band.values()])

print("  scope: %d pages enumerated from disk" % len(PAGES))
print("  internal footer hrefs validated against files on disk")
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - five columns, three principles, bs block intact, no dead links")
