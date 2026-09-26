#!/usr/bin/env python3
"""Gate for the holding-company site nav. Replaces qa/retired/check-nav-dropdown.py.

RULING: Rodney Smith, 2026-09-26 (_ops/rules/srs-holding-company-positioning.md, Q2).
The site is a holding company now. The nav is exactly:

    Home, About, FAQ, Contact      -> the four company pages on this site
    BidStrike, SLED Radar          -> OUT to bidstrike.cloud and sledradar.ai

WHAT THIS ASSERTS, on every chrome page:
  1. the desktop row (ul.nav-links) and the mobile drawer (nav.site-nav) both exist
     and carry exactly those six links, in that order, with those hrefs
  2. the drawer is the same list as the desktop row. Below 1080px the drawer is the
     ONLY navigation (styles.css hides .nav-links there), so a link missing from it
     is missing from the site on a phone
  3. both are identical across every chrome page, once aria-current is normalized,
     and aria-current sits on the link to THIS page and nowhere else
  4. product links are https, point at exactly the right host, open in a new tab,
     and carry rel=noopener
  5. no nav link points at a file that does not exist, or at a retired stub.
     Retired stubs are DERIVED, never listed: any page on disk that declares itself
     chromeless (marker + noindex). A hand list of retired pages would silently stop
     covering the day an eleventh page is retired.
  6. the .site-nav class and the #site-nav id the toggle controls are intact,
     because script.js binds the CLASS and the button's aria-controls names the id

SCOPE IS ENUMERATED FROM THE FILESYSTEM. Every *.html in the repo root that does
not declare itself chromeless is a chrome page and must carry the nav. A page that
carries the chromeless marker but is NOT noindex counts as chrome here (same rule
as check-bidstrike-surfaces.py), so a half-declared opt-out fails loudly instead of
silently escaping the gate.

The layout half of the nav contract (the row must not fold or overflow) lives in
check-bidstrike-surfaces.py check 6, because that is where the original reason for
it lives: bidstrike-landing shipped a folded nav row on 2026-08-05.

Run: python3 qa/check-site-nav.py   # exit 0 = pass
"""
import glob
import os
import re
import sys
from urllib.parse import urlsplit

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

CHROMELESS_MARKER = "brand-system: chromeless page"


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def is_chromeless(src):
    return CHROMELESS_MARKER in src and re.search(
        r'name=["\']robots["\'][^>]*noindex', src, re.I)


ALL = sorted(glob.glob("*.html"))
PAGES = [p for p in ALL if not is_chromeless(read(p))]
RETIRED = [p for p in ALL if p not in PAGES]

# THE RULED LIST. Order is asserted: company pages first, then products, and
# BidStrike leads every product list (ruled 2026-08-29, restated 2026-09-26).
INTERNAL = [("Home", "/"), ("About", "/about"), ("FAQ", "/faq"), ("Contact", "/contact")]
PRODUCTS = [("BidStrike", "bidstrike.cloud"), ("SLED Radar", "sledradar.ai")]
LABELS = [l for l, _ in INTERNAL] + [l for l, _ in PRODUCTS]

A_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
ROW_RE = re.compile(r'<ul class="nav-links">(.*?)</ul>', re.S)
DRAWER_RE = re.compile(r'<nav\b[^>]*\bclass="[^"]*\bsite-nav\b[^"]*"[^>]*>(.*?)</nav>', re.S)


def links(block):
    out = []
    for attrs, text in A_RE.findall(block):
        a = dict(ATTR_RE.findall(attrs))
        label = re.sub(r"<[^>]+>", "", text).strip()
        out.append((label, a))
    return out


def resolve(href):
    """Local file an internal href serves, or None when it is not internal."""
    if not href.startswith("/") or href.startswith("//"):
        return None
    path = urlsplit(href).path
    if path == "/":
        return "index.html"
    return path.strip("/") + ".html"


def self_href(page):
    return "/" if page == "index.html" else "/" + page[:-5]


fails = []
seen_row, seen_drawer = {}, {}

for p in PAGES:
    s = read(p)
    row_m, drawer_m = ROW_RE.search(s), DRAWER_RE.search(s)
    if not row_m:
        fails.append("%s  no desktop nav row (ul.nav-links)" % p)
    if not drawer_m:
        fails.append("%s  no mobile drawer (nav.site-nav). script.js binds the CLASS" % p)
    if not (row_m and drawer_m):
        continue
    if not re.search(r'<nav\b[^>]*\bid="site-nav"', s):
        fails.append("%s  drawer lost id=site-nav, which the toggle's aria-controls names" % p)
    if 'aria-controls="site-nav"' not in s:
        fails.append("%s  nav toggle no longer aria-controls the drawer" % p)

    for where, block, seen in (("row", row_m.group(1), seen_row),
                               ("drawer", drawer_m.group(1), seen_drawer)):
        ls = links(block)
        got = [l for l, _ in ls]
        if got != LABELS:
            fails.append("%s  %s links are %s\n      ruled (2026-09-26):  %s"
                         % (p, where, got, LABELS))
        for label, a in ls:
            href = a.get("href", "")
            cur = a.get("aria-current")
            internal = dict(INTERNAL).get(label)
            if internal is not None:
                if href != internal:
                    fails.append("%s  %s %r points at %r, ruled %r" % (p, where, label, href, internal))
                if cur is not None and (cur != "page" or href != self_href(p)):
                    fails.append("%s  %s %r carries aria-current=%r but this page is %s"
                                 % (p, where, label, cur, self_href(p)))
                if cur is None and href == self_href(p):
                    fails.append("%s  %s %r is this page but has no aria-current=page" % (p, where, label))
            product = dict(PRODUCTS).get(label)
            if product is not None:
                u = urlsplit(href.replace("&amp;", "&"))
                if u.scheme != "https":
                    fails.append("%s  %s %r is not https: %r" % (p, where, label, href))
                if u.netloc != product:
                    fails.append("%s  %s %r points at host %r, must be %r"
                                 % (p, where, label, u.netloc, product))
                if a.get("target") != "_blank":
                    fails.append("%s  %s %r does not open in a new tab" % (p, where, label))
                if "noopener" not in a.get("rel", "").split():
                    fails.append("%s  %s %r missing rel=noopener" % (p, where, label))
                if cur is not None:
                    fails.append("%s  %s %r is off-site and cannot be aria-current" % (p, where, label))
            # every internal href, ruled or not, must land on a live chrome page
            f = resolve(href)
            if f is not None:
                if not os.path.exists(f):
                    fails.append("%s  %s %r -> %s, which does not exist" % (p, where, label, f))
                elif f in RETIRED:
                    fails.append("%s  %s %r -> %s, a chromeless page (retired stub or "
                                 "link-only handout) that the nav must never reach" % (p, where, label, f))
        # identity across pages: normalize the one attribute that legitimately
        # differs (aria-current, asserted correct above) and compare the rest
        norm = re.sub(r'\s*aria-current="page"', "", block)
        norm = re.sub(r"\s+", " ", norm).strip()
        seen.setdefault(norm, []).append(p)

    # the drawer is the same list as the row, href for href
    row_pairs = [(l, a.get("href")) for l, a in links(row_m.group(1))]
    drw_pairs = [(l, a.get("href")) for l, a in links(drawer_m.group(1))]
    if row_pairs != drw_pairs:
        fails.append("%s  drawer does not mirror the desktop row\n      row:    %s\n      drawer: %s"
                     % (p, row_pairs, drw_pairs))

for name, seen in (("desktop row", seen_row), ("drawer", seen_drawer)):
    if len(seen) > 1:
        fails.append("%s differs between pages: %s" % (name, list(seen.values())))

print("  scope: %d chrome pages enumerated from disk -> %s" % (len(PAGES), ", ".join(PAGES)))
print("  chromeless, derived (marker + noindex; retired stubs and link-only handouts): %d -> %s"
      % (len(RETIRED), ", ".join(RETIRED)))
print("  ruled nav: %s" % " | ".join(LABELS))
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS - row and drawer identical on %d pages, six ruled links, "
      "products out in a new tab, no link to a stub or a missing file" % len(PAGES))
