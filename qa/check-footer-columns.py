#!/usr/bin/env python3
"""Gate for the footer columns and the operating-principles band.

RE-RULED 2026-09-26 to the holding-company structure (Rodney Smith,
_ops/rules/srs-holding-company-positioning.md, Q2; he approved re-ruling the gates
the same day). The five consulting-era columns became three: Company, Products,
Legal. Only COLS and the internal-link check changed; every other assertion in
this file still describes the live footer and is kept as it was.

SCOPE ENUMERATED FROM THE FILESYSTEM. Same reasoning as the retired
qa/retired/check-nav-dropdown.py: the
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

# RULED 2026-08-30: the footer is the SITEMAP. The single "Solutions" column
# split into two named groups so a reader can tell which lane a link belongs to,
# and the separate BidStrike chip came out as redundant against the funnel
# structure. BidStrike now rides as a LINK inside Construction Solutions.
# RE-RULED 2026-08-31: consulting is the PRIMARY lane and construction is
# secondary to it, on this surface and in the nav bracket. The labels also moved
# to match the nav exactly ("Consulting and Strategy" / "Construction Software"),
# because the footer and the nav had been calling the same two groups by
# different names since the nav rebuild.
#
# THIS LIST IS ORDERED AND THE ORDER IS ASSERTED BELOW. Presence alone was
# checked until this date, and presence alone is exactly what lets a ruling about
# ORDER quietly revert on the next person's edit - the same failure the nav gate
# hit on 8/29 with the BidStrike lockup.
#
# RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
#   OLD assertion: five columns in order, Consulting and Strategy | Construction
#                  Software | Resources | Company | Legal.
#   NEW assertion: three columns in order, Company | Products | Legal.
# The consulting lane is gone, so "consulting leads" no longer has a subject.
# Order is still asserted, not just presence, for the reason above: Company (the
# site itself) leads, the products it owns follow, Legal closes. What the Products
# column must CONTAIN (both products, linking out, BidStrike first) is asserted in
# check-bidstrike-surfaces.py check 5, so the two gates cannot deadlock over it.
COLS = ["Company", "Products", "Legal"]
# The authoritative wording, confirmed by Rodney 2026-07-23. The five
# reverse-engineered "Brand values" were DELETED from srs-brand-voice.md on
# 2026-08-18 and must never come back - two layers remain, purpose and these three.
PRINCIPLES = ["Full Disclosure", "Congruence", "Excellent Service"]
BANNED_VALUES = ["Brand values", "Brand Values"]

# RULED BY RODNEY 2026-08-28. The principles used to render as a full band with
# <h4> headings and paragraph copy on ALL 13 pages, which is the failure mode the
# AI-disclosure doctrine names for a different element: a block repeated on every
# page "reads as boilerplate inside two weeks." The principles are the strongest
# thing SRS publishes, and repetition was draining them.
#
# The new rule, and this gate is the only thing holding the two variants apart:
#   * FULL treatment, headings + paragraphs, on about.html ONLY.
#   * SKINNY strip, names only, INSIDE <footer>, on every chrome page.
#   * about.html therefore carries BOTH. Rodney was shown that duplication
#     directly and chose it. It is a decision, not an oversight - do not
#     "fix" it by exempting About from the strip.
#
# Both variants keep their own cross-page drift check. Splitting one sitewide
# block into two variants is exactly how chrome starts drifting per page, so the
# identity assertions get STRONGER here, not weaker.
FULL_BAND_PAGE = "about.html"

# RE-RULED 2026-09-26.
#   OLD assertion: a footer href that appears in a hand-maintained CANDIDATES map
#                  of twelve paths must resolve to a file that exists.
#   NEW assertion: EVERY internal footer href must resolve to a file that exists
#                  AND is a live chrome page, not a chromeless retired stub.
# Why it moved: ten of those twelve paths were retired to redirect stubs on
# 2026-09-26. The files still exist, so the old check would have PASSED a footer
# link to /what-we-do that bounces the reader home. And a hand list only covers
# what someone remembered to add. Both halves are now derived from disk.
def _chromeless(src):
    return "brand-system: chromeless page" in src and re.search(
        r'name=["\']robots["\'][^>]*noindex', src, re.I)


RETIRED = [p for p in sorted(glob.glob("*.html"))
           if _chromeless(open(p, encoding="utf-8").read())]


def resolve(href):
    path = href.split("#")[0].split("?")[0]
    return "index.html" if path == "/" else path.strip("/") + ".html"

fails = []
foot_re = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)
band_re = re.compile(r'<section class="principles-band".*?</section>', re.S)
strip_re = re.compile(r'<section class="foot-principles".*?</section>', re.S)
seen_strip = {}

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
    # The .bs-footer-block chip was RETIRED 2026-08-30 when the footer became the
    # sitemap. This gate used to require it and pointed at check-bidstrike-surfaces
    # as the reason, so the two gates held each other in place. That sibling check
    # now asserts the replacement instead: a BidStrike link inside the Construction
    # Solutions group. Requiring the chip here as well would deadlock the pair.
    if 'class="bs-footer-block"' in foot:
        fails.append("%s  the retired .bs-footer-block chip is back in the footer" % p)
    for c in COLS:
        if ">%s<" % c not in foot:
            fails.append("%s  footer missing column -> %s" % (p, c))
    # ORDER, not just presence. Company leads, Products, then Legal (2026-09-26).
    present = [c for c in COLS if ">%s<" % c in foot]
    actual = sorted(present, key=lambda c: foot.index(">%s<" % c))
    if actual != present:
        fails.append("%s  footer columns are out of order.\n      on the page: %s"
                     "\n      should be:   %s\n      Company leads, then the "
                     "products it owns, then Legal (ruled 2026-09-26)"
                     % (p, " | ".join(actual), " | ".join(present)))

    # no footer link may point at a page that does not exist, or at a stub
    for href in re.findall(r'href="(/(?!/)[^"]*)"', foot):
        if href.startswith("/assets/"):
            continue
        f = resolve(href)
        if not os.path.exists(f):
            fails.append("%s  footer links %s but %s does not exist" % (p, href, f))
        elif f in RETIRED:
            fails.append("%s  footer links %s, a chromeless retired stub that "
                         "redirects away (retired 2026-09-26)" % (p, href))

    # the skinny strip is sitewide chrome and lives INSIDE the footer
    st = strip_re.search(foot)
    if not st:
        fails.append("%s  footer missing .foot-principles - the skinny names-only "
                     "strip is sitewide chrome (ruled 8/28)" % p)
    else:
        seen_strip.setdefault(st.group(0), []).append(p)
        for pr in PRINCIPLES:
            if pr not in st.group(0):
                fails.append("%s  footer principles strip missing -> %s" % (p, pr))
        if "<p" in st.group(0) or "<h4" in st.group(0):
            fails.append("%s  footer principles strip carries headings or paragraph "
                         "copy - names ONLY. The full treatment belongs on %s alone, "
                         "or the strip becomes the boilerplate this split removed"
                         % (p, FULL_BAND_PAGE))

    # the full band with its paragraphs belongs on exactly one page
    b = band_re.search(s)
    if p == FULL_BAND_PAGE:
        if not b:
            fails.append("%s  missing the full .principles-band - this is the ONE "
                         "page that carries the full treatment (ruled 8/28)" % p)
        else:
            for pr in PRINCIPLES:
                if pr not in b.group(0):
                    fails.append("%s  principles band missing -> %s" % (p, pr))
            if "<p" not in b.group(0):
                fails.append("%s  the full band lost its paragraph copy - that copy "
                             "is the whole reason one page keeps the full treatment"
                             % p)
    elif b:
        fails.append("%s  still carries the full .principles-band. It belongs on %s "
                     "only; every other page gets the skinny footer strip (ruled 8/28)"
                     % (p, FULL_BAND_PAGE))

    for bv in BANNED_VALUES:
        if bv in s:
            fails.append('%s  the deleted "%s" layer is back - only purpose and '
                         "the three principles survive (ruled 8/18)" % (p, bv))

# the skinny strip is site-wide chrome, so it drifts the same way the footer does
if len(seen_strip) > 1:
    fails.append("footer principles strip differs between pages: %s"
                 % [v for v in seen_strip.values()])

print("  scope: %d pages enumerated from disk" % len(PAGES))
print("  internal footer hrefs validated against files on disk and %d derived "
      "chromeless stubs" % len(RETIRED))
print("  full principles band expected on %s only; skinny footer strip on all %d"
      % (FULL_BAND_PAGE, len(PAGES)))
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - %s in order, full band on %s only, skinny strip on all %d, "
      "no dead or retired internal links" % (" | ".join(COLS), FULL_BAND_PAGE, len(PAGES)))
