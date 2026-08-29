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

# Internal hrefs the footer may offer, gated on the page existing.
CANDIDATES = {"/construction": "construction.html",
              "/what-we-do":   "what-we-do.html",
              "/operator-os":  "operator-os.html",
              "/results":      "results.html",
              "/events":       "events.html",
              "/faq":          "faq.html",
              "/about":        "about.html",
              "/is-this-you":  "is-this-you.html",
              "/contact":      "contact.html",
              "/privacy":      "privacy.html",
              "/work-together":"work-together.html"}

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
print("  internal footer hrefs validated against files on disk")
print("  full principles band expected on %s only; skinny footer strip on all %d"
      % (FULL_BAND_PAGE, len(PAGES)))
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - five columns, full band on %s only, skinny strip on all %d, "
      "bs block intact, no dead links" % (FULL_BAND_PAGE, len(PAGES)))
