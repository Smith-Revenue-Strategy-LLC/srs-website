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

REBUILT 2026-08-31 to the two-group bracket. The checks added at the bottom exist
because every check above this one passes on a panel whose who-buys-it lines have
been deleted - the hrefs and lockups would still be present and the gate would
still report PASS on a dropdown that had lost the only reason it was rebuilt.

Run: python3 qa/check-nav-dropdown.py   # exit 0 = pass
"""
import glob, sys, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

CHROMELESS = "brand-system: chromeless page"
PAGES = [p for p in sorted(glob.glob("*.html"))
         if CHROMELESS not in open(p, encoding="utf-8").read()]

# Candidate product/lane rows, and the file each would resolve to.
CANDIDATES = {"/construction": "construction.html",
              "/what-we-do":   "what-we-do.html",
              "/operator-os":  "operator-os.html",
              "/ai-peer-group": "ai-peer-group.html",
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
    # SCOPE THE SEARCH TO THE DROPDOWN PANEL. Until 2026-08-30 this checked the
    # whole page, so a FOOTER link to the same href satisfied it and the row could
    # be missing from the nav entirely. That is exactly what happened when
    # ai-peer-group.html was added: it had the footer link, no nav row, and this
    # gate reported PASS. A gate that any link on the page can satisfy is not
    # checking the dropdown.
    panel = " ".join(re.findall(r'<div class="nav-drop-panel">.*?</div>\s*</li>', s, re.S)) or ""
    for r in sorted(EXPECTED):
        if 'href="%s"' % r not in panel:
            fails.append("%s  dropdown missing row for an EXISTING page -> %s "
                         "(searched the .nav-drop-panel only)" % (p, r))
    for r in sorted(ABSENT):
        if 'href="%s"' % r in s:
            fails.append("%s  dropdown promises %s but %s does not exist"
                         % (p, r, CANDIDATES[r]))
    for b in BRANDS:
        if b not in s:
            fails.append("%s  dropdown missing product lockup -> %s" % (p, b))
    # ORDER IS A RULING, NOT A LAYOUT ACCIDENT. Rodney, 2026-08-29: BidStrike is
    # the most established product and the one he is marketing hardest, so it
    # leads every product list. Presence alone was checked before this date and
    # presence alone lets the order drift back on the next page someone edits.
    if all(b in s for b in BRANDS):
        if s.index(BRANDS[1]) > s.index(BRANDS[0]):
            fails.append("%s  SLED RADAR lockup precedes BidStrike. BidStrike leads "
                         "every product list (ruled 8/29)" % p)
    if 'class="site-nav' not in s:
        fails.append("%s  .site-nav contract broken (script.js binds the CLASS)" % p)
    # keyboard access is not optional - hover-only ships a nav no tab user can open
    if 'aria-haspopup' not in s:
        fails.append("%s  dropdown trigger missing aria-haspopup" % p)

    # ----------------------------------------------------------------------
    # THE 2026-08-31 REBUILD. Rodney's spec: two main groups, products nested
    # under each, and BESIDE EVERY PRODUCT A LINE SAYING WHO BUYS IT - so a
    # visitor reads the problem a product addresses without opening a page.
    #
    # That last part is the entire reason the rebuild happened, and until this
    # block existed the gate could not see it. Every check above passes on a
    # panel with the descriptions stripped out: the hrefs would still be there,
    # the lockups would still be there, and the gate would still say PASS on a
    # dropdown that had lost its whole point. Structure is not the feature.
    # ----------------------------------------------------------------------
    if '<button class="nav-drop-trigger' not in s:
        fails.append("%s  trigger must be a <button>. Results left this tab on "
                     "2026-08-31, so the control navigates nowhere and an anchor "
                     "would have to name a destination it does not have" % p)
    # The panel is CSS :hover / :focus-within with no JS behind it, so a static
    # aria-expanded tells every screen reader the menu is shut while it is open.
    if 'aria-expanded="false" aria-haspopup' in s or 'aria-haspopup="true" aria-expanded' in s:
        fails.append("%s  trigger carries a static aria-expanded that nothing "
                     "updates. The panel is pure CSS; the attribute is a lie" % p)
    if 'href="/results"' in s.split('<div class="nav-drop-panel">')[0]:
        fails.append("%s  Results is still a top-level tab. The spec moves it "
                     "inside, as a subsidiary of each group" % p)

    groups = panel.split('<div class="nav-drop-group">')[1:]
    if len(groups) != 2:
        fails.append("%s  expected 2 nav-drop-groups (Consulting and Strategy, "
                     "Construction Software), found %d" % (p, len(groups)))
    for label, want in (("Consulting and Strategy", "/what-we-do"),
                        ("Construction Software", "/construction")):
        if label not in panel:
            fails.append("%s  dropdown missing group head %r" % (p, label))
        elif 'href="%s"' % want not in panel:
            fails.append("%s  group head %r must link to %s" % (p, label, want))
    # Results is a subsidiary of BOTH groups, not one shared row at the foot.
    for i, g in enumerate(groups):
        if 'nav-drop-name">Results<' not in g:
            fails.append("%s  group %d has no Results row. It is a subsidiary of "
                         "each group, not a shared one (ruled 8/31)" % (p, i + 1))
    # WHO BUYS IT, one line per row, counted rather than sampled.
    for i, g in enumerate(groups):
        rows = g.count("<a ")
        whos = g.count('class="nav-drop-who"')
        if rows != whos:
            fails.append("%s  group %d has %d rows but %d who-buys-it lines. Every "
                         "row carries one - that is the rebuild" % (p, i + 1, rows, whos))

    # The drawer is the ONLY navigation below 1080px, where .nav-links and the
    # panel are both display:none. It mirrors the same bracket.
    nav = " ".join(re.findall(r'<nav[^>]*\bclass="[^"]*\bsite-nav\b[^"]*".*?</nav>', s, re.S))
    if nav.count('class="site-nav-head"') != 2:
        fails.append("%s  mobile drawer must mirror both groups (found %d heads)"
                     % (p, nav.count('class="site-nav-head"')))
    if 'class="site-nav-sub"' not in nav:
        fails.append("%s  mobile drawer groups have no nested rows" % p)
    # Standing rule, enforced next door in check-bidstrike-surfaces.py: the nav is
    # the site's identity statement and is not a placement. Restated here so the
    # next person to "finish mirroring the bracket" reads it before trying.
    if "bidstrike" in nav.lower():
        fails.append("%s  BidStrike named in the drawer. The nav is not a "
                     "placement; it is reached through Construction Software" % p)

print("  scope: %d pages enumerated from disk -> %s" % (len(PAGES), ", ".join(PAGES)))
print("  rows REQUIRED (page exists on disk): %s" % (", ".join(sorted(EXPECTED)) or "none"))
print("  rows FORBIDDEN (page absent)       : %s" % (", ".join(sorted(ABSENT)) or "none"))
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - dropdown rows match what exists, lockups and JS contract intact")
