#!/usr/bin/env python3
"""Gate for the Solutions & Results dropdown.

SCOPE IS ENUMERATED FROM THE FILESYSTEM, never a hand-maintained list - a gate whose
scope is a hand list silently stops covering and keeps reporting PASS.

That applies to the dropdown ROWS too, and it is why this differs from the 8/24 plan's
draft. The draft hardcoded ROWS = [/construction, /operator-os, /results]. /operator-os
is Tier 2 and does not exist yet, so that gate would have DEMANDED a nav row pointing at
a 404 - the exact thing the sprint's own honesty rule forbids. Instead:

  - every product page that EXISTS on disk must have a dropdown row, and
  - no dropdown row may point at a page that does NOT exist.

Both directions matter. The first catches a page shipped without navigation; the second
catches a nav promise the site cannot keep. When /operator-os lands, this gate starts
requiring its row automatically, with no edit here.

Run: python3 qa/check-nav-dropdown.py   # exit 0 = pass
"""
import glob, sys, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

CHROMELESS = "brand-system: chromeless page"
PAGES = [p for p in sorted(glob.glob("*.html"))
         if CHROMELESS not in open(p, encoding="utf-8").read()]

# Candidate product/lane rows, and the file each would resolve to.
CANDIDATES = {"/construction": "construction.html",
              "/operator-os":  "operator-os.html",
              "/results":      "results.html"}
EXPECTED = {r for r, f in CANDIDATES.items() if os.path.exists(f)}
ABSENT   = {r for r, f in CANDIDATES.items() if not os.path.exists(f)}
# NOT the domains. check-bidstrike-surfaces.py enforces a standing rule that no
# BidStrike LINK may appear in site navigation, so the products ride in the dropdown
# as LOCKUP ART inside a row that points at an SRS page. Checking for the domain
# strings here would have demanded the exact markup that rule forbids - it did, on
# 2026-08-27, and the two gates deadlocked until this was corrected.
BRANDS   = ["brand/sled-radar.svg", "brand/bidstrike-logo.png"]

fails = []
for p in PAGES:
    s = open(p, encoding="utf-8").read()
    if 'class="nav-drop"' not in s:
        fails.append("%s  missing .nav-drop" % p)
    if 'class="nav-drop-panel"' not in s:
        fails.append("%s  missing .nav-drop-panel" % p)
    for r in sorted(EXPECTED):
        if 'href="%s"' % r not in s:
            fails.append("%s  dropdown missing row for an EXISTING page -> %s" % (p, r))
    for r in sorted(ABSENT):
        if 'href="%s"' % r in s:
            fails.append("%s  dropdown promises %s but %s does not exist"
                         % (p, r, CANDIDATES[r]))
    for b in BRANDS:
        if b not in s:
            fails.append("%s  dropdown missing product lockup -> %s" % (p, b))
    if 'class="site-nav' not in s:
        fails.append("%s  .site-nav contract broken (script.js binds the CLASS)" % p)
    # keyboard access is not optional - hover-only ships a nav no tab user can open
    if 'aria-haspopup' not in s:
        fails.append("%s  dropdown trigger missing aria-haspopup" % p)

print("  scope: %d pages enumerated from disk -> %s" % (len(PAGES), ", ".join(PAGES)))
print("  rows REQUIRED (page exists on disk): %s" % (", ".join(sorted(EXPECTED)) or "none"))
print("  rows FORBIDDEN (page absent)       : %s" % (", ".join(sorted(ABSENT)) or "none"))
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - dropdown rows match what exists, lockups and JS contract intact")
