#!/usr/bin/env python3
"""
Regression gate for the BidStrike cross-surface placements.

Run after ANY edit that touches a bidstrike.cloud link, the footer, or the nav:

    python3 qa/check-bidstrike-surfaces.py     # exit 0 = pass

Every check below exists because the failure it catches has already happened
once, on this site or on bidstrike-landing. Do not delete a check to make the
suite green.
"""

import glob
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PAGES = sorted(glob.glob("*.html"))
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


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# Every <a ...> tag that points at bidstrike.cloud, with its source page.
LINK_RE = re.compile(r"<a\b[^>]*bidstrike\.cloud[^>]*>", re.I)
ATTR_RE = re.compile(r'(\w[\w-]*)\s*=\s*"([^"]*)"')


def bidstrike_links():
    out = []
    for page in PAGES:
        for tag in LINK_RE.findall(read(page)):
            attrs = dict(ATTR_RE.findall(tag))
            out.append((page, tag, attrs))
    return out


LINKS = bidstrike_links()


# --------------------------------------------------------------------------
# 1. The invisible-link bug.
# This stylesheet has NO inline text-link style. A bare <a> inside a paragraph
# renders identical to the sentence around it, so the link is real, clickable,
# and completely unseeable. Every outbound link must carry a bs- class.
# --------------------------------------------------------------------------
@check("every bidstrike link carries a visible bs- class")
def _():
    bad = []
    for page, tag, attrs in LINKS:
        classes = attrs.get("class", "")
        if not any(c.startswith("bs-") for c in classes.split()):
            bad.append("%s: class=%r would render as invisible prose" % (page, classes))
    return bad


# --------------------------------------------------------------------------
# 2. Outbound hygiene.
# --------------------------------------------------------------------------
@check("every bidstrike link opens in a new tab with rel=noopener")
def _():
    bad = []
    for page, tag, attrs in LINKS:
        if attrs.get("target") != "_blank":
            bad.append("%s: missing target=_blank" % page)
        if "noopener" not in attrs.get("rel", ""):
            bad.append("%s: missing rel=noopener" % page)
    return bad


# --------------------------------------------------------------------------
# 3. Attribution. Half the point of these placements is lead flow, which is
# unmeasurable if the links are untagged or share a campaign name.
# --------------------------------------------------------------------------
@check("every bidstrike link is utm-tagged with a unique campaign")
def _():
    bad = []
    campaigns = {}
    for page, tag, attrs in LINKS:
        href = html.unescape(attrs.get("href", ""))
        for key in ("utm_source=srs", "utm_medium=site", "utm_campaign="):
            if key not in href:
                bad.append("%s: href missing %s" % (page, key))
        m = re.search(r"utm_campaign=([^&\s\"]+)", href)
        if m:
            campaigns.setdefault(m.group(1), []).append(page)
    for name, pages in campaigns.items():
        # the footer is intentionally site-wide; everything else is one place
        if name != "footer" and len(pages) > 1:
            bad.append("campaign %r reused on %s" % (name, pages))
    notes.append("campaigns: %s" % ", ".join(sorted(campaigns)))
    return bad


# --------------------------------------------------------------------------
# 4. Customer disclosure.
# bidstrike.cloud was scrubbed on 2026-08-06 because a stranger could identify
# the sole tenant in two clicks. Naming that customer here, on a site that
# links across, rebuilds the same leak from the other end. Describe the
# vertical, never the account. Same rule for the app host.
# --------------------------------------------------------------------------
@check("no customer name and no app host anywhere on the site")
def _():
    banned = [
        "texas welding",
        "texasweldingcompany",
        "twc.bidstrike",
        "kennan",
        "westbrook",
    ]
    bad = []
    for page in PAGES + ["styles.css", "script.js"]:
        low = read(page).lower()
        for term in banned:
            if term in low:
                bad.append("%s: contains %r" % (page, term))
    return bad


# --------------------------------------------------------------------------
# 5. The footer is site-wide and must stay byte-identical across pages.
# --------------------------------------------------------------------------
@check("bidstrike footer block present and identical on all pages")
def _():
    block = re.compile(r'<div class="bs-footer-block">.*?</div>', re.S)
    seen = {}
    bad = []
    for page in PAGES:
        m = block.search(read(page))
        if not m:
            bad.append("%s: no bs-footer-block" % page)
            continue
        seen.setdefault(m.group(0), []).append(page)
    if len(seen) > 1:
        bad.append("footer block differs between pages: %s" % [v for v in seen.values()])
    notes.append("footer block on %d/%d pages" % (sum(len(v) for v in seen.values()), len(PAGES)))
    return bad


# --------------------------------------------------------------------------
# 6. The nav is the site's identity statement and is deliberately NOT a
# placement. bidstrike-landing shipped a folded nav row on 2026-08-05 by
# adding one link too many; a wrapped nav still looks like it rendered.
# --------------------------------------------------------------------------
@check("nav row untouched: no bidstrike link in site navigation")
def _():
    nav_re = re.compile(r'<nav class="site-nav".*?</nav>', re.S)
    bad = []
    counts = set()
    for page in PAGES:
        m = nav_re.search(read(page))
        if not m:
            bad.append("%s: no site-nav found" % page)
            continue
        nav = m.group(0)
        if "bidstrike" in nav.lower():
            bad.append("%s: bidstrike link added to the nav row" % page)
        counts.add(nav.count("<a "))
    if len(counts) > 1:
        bad.append("nav link count differs across pages: %s" % sorted(counts))
    notes.append("nav anchors per page: %s" % sorted(counts))
    return bad


# --------------------------------------------------------------------------
# 7. Structured data. This is the placement with the highest reach and the
# lowest visibility, so nothing on screen will tell you when it breaks.
# --------------------------------------------------------------------------
@check("index.html json-ld parses and declares the software node")
def _():
    src = read("index.html")
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', src, re.S
    )
    bad = []
    parsed = []
    for i, raw in enumerate(blocks):
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            bad.append("block %d is not valid JSON: %s" % (i, exc))
    if bad:
        return bad

    org = next((b for b in parsed if b.get("@type") == "ProfessionalService"), None)
    app = next((b for b in parsed if b.get("@type") == "SoftwareApplication"), None)

    if org is None:
        bad.append("ProfessionalService node missing")
    elif "https://bidstrike.cloud" not in org.get("sameAs", []):
        bad.append("bidstrike.cloud not in ProfessionalService sameAs")

    if app is None:
        bad.append("SoftwareApplication node missing")
    else:
        if app.get("url") != "https://bidstrike.cloud":
            bad.append("SoftwareApplication url is %r" % app.get("url"))
        pub = app.get("publisher", {}).get("@id")
        if pub != "https://smithrevenuestrategy.com/#organization":
            bad.append("SoftwareApplication publisher @id is %r" % pub)
        # never claim ratings or prices we do not have
        for fabricated in ("aggregateRating", "review", "offers"):
            if fabricated in app:
                bad.append("SoftwareApplication carries unsourced %r" % fabricated)

    notes.append("json-ld blocks parsed: %d" % len(parsed))
    return bad


# --------------------------------------------------------------------------
# 8. The five placements exist where they are supposed to.
# --------------------------------------------------------------------------
@check("all five placements present on their expected pages")
def _():
    expected = {
        "index.html": ["bs-band", "utm_campaign=home-band"],
        "work-together.html": ["utm_campaign=work-together-paths"],
        "results.html": ["bs-case", "utm_campaign=results-case"],
        "about.html": ["built-tray", "utm_campaign=about-tray"],
        "is-this-you.html": ["situation_c", "utm_campaign=is-this-you"],
        "faq.html": ["utm_campaign=faq"],
    }
    bad = []
    for page, needles in expected.items():
        src = read(page)
        for needle in needles:
            if needle not in src:
                bad.append("%s: missing %r" % (page, needle))
    return bad


# --------------------------------------------------------------------------
# 9. Ownership disclosure. BidStrike is Rodney's own company, not a partner
# referral. The /about tray sits directly under a tray whose closing line
# describes revenue-share referrals, so the distinction has to be explicit.
# --------------------------------------------------------------------------
@check("ownership disclosed on /about and /results")
def _():
    bad = []
    about = read("about.html")
    tray = about.split('id="built-tray"', 1)
    if len(tray) < 2:
        bad.append("about.html: built-tray missing")
    elif "own bidstrike outright" not in tray[1].lower():
        bad.append("about.html: built-tray does not state outright ownership")
    if "my own product" not in read("results.html").lower():
        bad.append("results.html: case block does not disclose ownership")
    return bad


# --------------------------------------------------------------------------
# 10. The full-width-slab bug.
# Several card classes are `display: grid`. An inline-flex child inside one
# gets blockified and stretches the whole track, so .bs-cta renders as a
# full-width slab next to a compact .button neighbour (which escapes via its
# own `width: fit-content` rule). Caught on /is-this-you before launch.
# Any card class that is BOTH a grid container AND hosts a .bs-cta must carry
# a matching fit-content override.
# --------------------------------------------------------------------------
@check("no .bs-cta can stretch inside a grid card")
def _():
    css = read("styles.css")

    grid_containers = set()
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sels, body = m.group(1), m.group(2)
        if re.search(r"display:\s*grid", body):
            for sel in sels.split(","):
                sel = sel.strip()
                if re.fullmatch(r"\.[\w-]+", sel):
                    grid_containers.add(sel[1:])

    # A character window around the opening tag is not containment: it bleeds
    # past the element's own closing tag into whatever follows. Track the real
    # open-element stack instead so ancestry is exact.
    class Ancestry(HTMLParser):
        VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                "link", "meta", "param", "source", "track", "wbr"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack = []
            self.pairs = []  # (grid-container-class, ) for each .bs-cta found

        def handle_starttag(self, tag, attrs):
            classes = dict(attrs).get("class", "").split()
            if "bs-cta" in classes and self.stack:
                # Only the IMMEDIATE parent matters: grid stretching applies to
                # grid items, i.e. direct children. An outer grid further up the
                # tree (.situation-grid wrapping .situation-card) does not
                # stretch a grandchild.
                for c in self.stack[-1]:
                    if c in grid_containers:
                        self.pairs.append(c)
            if tag not in self.VOID:
                self.stack.append(classes)

        def handle_startendtag(self, tag, attrs):
            pass  # self-closing: never becomes an ancestor

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

    bad = []
    checked = []
    for page in PAGES:
        parser = Ancestry()
        parser.feed(read(page))
        for host in set(parser.pairs):
            checked.append("%s .bs-cta" % host)
            rule = re.search(r"\.%s\s+\.bs-cta\s*\{([^{}]*)\}" % re.escape(host), css)
            if not rule or "fit-content" not in rule.group(1):
                bad.append(
                    "%s: .bs-cta inside grid container .%s with no "
                    "`width: fit-content` override" % (page, host)
                )
    notes.append("grid-hosted cta pairs checked: %s" % (sorted(set(checked)) or "none"))
    return bad


# --------------------------------------------------------------------------
print("-" * 62)
for n in notes:
    print("note  %s" % n)
print("-" * 62)
if failures:
    print("FAILED %d of %d checks" % (len(failures), len(failures) + 0 or len(failures)))
    sys.exit(1)
print("all checks passed (%d pages)" % len(PAGES))
sys.exit(0)
