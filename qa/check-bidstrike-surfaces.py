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
import struct
import sys
from html.parser import HTMLParser

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PAGES = sorted(glob.glob("*.html"))

# A page may opt OUT of the site chrome, but only by saying so out loud: it has
# to be noindex AND carry the marker below. This is the SAME declaration
# check-brand-system.py honors, kept byte-identical in intent on purpose - two
# gates disagreeing about what a legitimate page looks like is how one of them
# ends up permanently red and stops being read. The chrome checks (footer block,
# nav row, header wordmark) are the only ones that skip these pages. Every other
# check here - link classes, utm tags, customer-name ban - still applies to them.
CHROMELESS_MARKER = "brand-system: chromeless page"


def _is_chromeless(src):
    return CHROMELESS_MARKER in src and re.search(
        r'name=["\']robots["\'][^>]*noindex', src, re.I)


CHROME_PAGES = [p for p in PAGES
                if not _is_chromeless(open(p, encoding="utf-8").read())]
CHROMELESS_PAGES = [p for p in PAGES if p not in CHROME_PAGES]

failures = []
notes = ["chrome scope: %d of %d pages; chromeless by declaration: %s"
         % (len(CHROME_PAGES), len(PAGES), ", ".join(CHROMELESS_PAGES) or "none")]


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
@check("every bidstrike link is visibly styled, by a bs- class or its container")
def _():
    """The point of this check is that a BidStrike link must RENDER as something,
    not as unstyled prose the eye slides past. A bs- class was the only way that
    happened until 2026-08-30.

    The footer sitemap added a second legitimate way: a plain <a> inside
    .foot-col, which styles its own anchors. Asserting a bs- class there would
    force a monospace lime-underlined .bs-link into a column of plain footer
    links, which is a worse footer, so the CONTAINER counts as styling.

    This is a widening of the accepted contexts, not of the rule. A BidStrike
    link that is neither bs-classed nor inside .foot-col still fails.

    RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
      OLD assertion: a bs- class, or inside .foot-col.
      NEW assertion: a bs- class, or a card class from STYLED_CARDS that
                     styles.css actually defines, or inside a container that
                     styles its own anchors: .foot-col, the desktop nav row
                     (ul.nav-links) or the mobile drawer (nav.site-nav).
    Why: the ruling puts BidStrike in the nav, and the homepage product card is
    a .solution-chip whose whole face is the link. Both render as a visible
    control; neither can be prose. The rule is unchanged: a link that is none of
    these still fails. Each card class is checked against styles.css so a class
    name that styles nothing cannot count as styling."""
    STYLED_CARDS = {"solution-chip"}
    css = read("styles.css")
    bad = ["styles.css defines no .%s rule, so it cannot count as styling" % c
           for c in sorted(STYLED_CARDS)
           if not re.search(r"(^|[\s,}])\.%s\s*\{" % re.escape(c), css)]
    containers = [re.compile(r'<div class="foot-col">.*?</div>', re.S),
                  re.compile(r'<ul class="nav-links">.*?</ul>', re.S),
                  re.compile(r'<nav\b[^>]*\bclass="[^"]*\bsite-nav\b[^"]*".*?</nav>', re.S)]
    cols = {p: " ".join(" ".join(c.findall(read(p))) for c in containers)
            for p in {l[0] for l in LINKS}}
    for page, tag, attrs in LINKS:
        classes = attrs.get("class", "").split()
        if any(c.startswith("bs-") for c in classes):
            continue
        if STYLED_CARDS & set(classes):
            continue
        if tag in cols.get(page, ""):
            continue
        bad.append("%s: class=%r and not inside .foot-col or the nav, so it "
                   "would render as invisible prose" % (page, " ".join(classes)))
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
    # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
    #   OLD assertion: every campaign is used once, except "footer", which may
    #                  repeat anywhere.
    #   NEW assertion: every campaign is used once, except the two SITE-WIDE
    #                  CHROME campaigns, "footer" and "nav", and each of those may
    #                  repeat ONLY inside its own chrome region (the footer, or
    #                  the nav row + drawer). Anywhere else it is a reuse.
    # Why nav joins footer: the ruling puts BidStrike in the nav, and the nav is
    # chrome that check 6 and check-site-nav.py hold byte-identical across every
    # page. A per-page campaign would break that identity to answer a question
    # nobody asked; the question this rule exists for is WHICH SURFACE sent the
    # visit (nav vs footer vs a body placement), and one name per surface still
    # answers it. The row and the drawer share the name because they are one nav
    # at two widths, never on screen together.
    # Why the region pin is new: the old exemption let "footer" appear in a body
    # paragraph and still pass, which would have silently merged two surfaces.
    SITEWIDE = {
        "footer": [re.compile(r'<footer class="site-footer">.*?</footer>', re.S)],
        "nav": [re.compile(r'<ul class="nav-links">.*?</ul>', re.S),
                re.compile(r'<nav\b[^>]*\bclass="[^"]*\bsite-nav\b[^"]*".*?</nav>', re.S)],
    }
    for page, tag, attrs in LINKS:
        m = re.search(r"utm_campaign=([^&\s\"]+)", html.unescape(attrs.get("href", "")))
        if m and m.group(1) in SITEWIDE:
            region = " ".join(" ".join(r.findall(read(page))) for r in SITEWIDE[m.group(1)])
            if tag not in region:
                bad.append("%s: campaign %r used outside its own chrome region"
                           % (page, m.group(1)))
    for name, pages in campaigns.items():
        if name not in SITEWIDE and len(pages) > 1:
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
@check("bidstrike present in the footer sitemap, identical on all pages")
def _():
    """RULED 2026-08-30. The standalone .bs-footer-block chip ("Also built here"
    plus the lockup) is GONE - Rodney called it redundant once the footer became
    the sitemap and the funnel structure carried the same job. BidStrike now
    rides as a LINK inside the Construction Solutions group.

    This assertion did not weaken with the chip. It still requires BidStrike on
    every chrome page, still requires the footer to be identical across pages,
    and it now ALSO pins the link to the Construction Solutions group rather
    than accepting it anywhere in the footer. The old check would have passed on
    a BidStrike link dropped into any column."""
    foot = re.compile(r'<footer class="site-footer">.*?</footer>', re.S)
    seen = {}
    bad = []
    for page in CHROME_PAGES:
        m = foot.search(read(page))
        if not m:
            bad.append("%s: no site-footer" % page)
            continue
        f = m.group(0)
        if "bs-footer-block" in f:
            bad.append("%s: the retired .bs-footer-block chip is back" % page)
        # the link has to sit in the products group, not merely in the footer
        # RENAMED 2026-08-31 with the footer reorder: "Construction Solutions"
        # became "Construction Software" to match the nav bracket.
        #
        # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
        #   OLD assertion: BidStrike sits in a "Construction Software" column and
        #                  points INWARD at /construction#bidstrike; an outward
        #                  bidstrike.cloud link there FAILS (ruled 8/31: outward
        #                  skipped the SRS page that qualified the buyer).
        #   NEW assertion: BidStrike sits in the "Products" column and points OUT
        #                  at https://bidstrike.cloud, SLED Radar sits beside it
        #                  pointing OUT at https://sledradar.ai, BidStrike first;
        #                  an inward link to /construction FAILS.
        # Why it inverted again: the qualifying page /construction is now a
        # chromeless redirect stub. Pointing inward would send the reader to a
        # page that bounces them home. The product sites are where the work
        # happens now, per the approved brand paragraph.
        grp = re.search(r'<h5>Products</h5>(.*?)</div>', f, re.S)
        if not grp:
            bad.append("%s: no Products column in the footer" % page)
        else:
            g = grp.group(1)
            bs = g.find('href="https://bidstrike.cloud/')
            sr = g.find('href="https://sledradar.ai/')
            if bs < 0:
                bad.append("%s: BidStrike missing from the Products column, or not "
                           "pointing OUT at https://bidstrike.cloud" % page)
            if sr < 0:
                bad.append("%s: SLED Radar missing from the Products column, or not "
                           "pointing OUT at https://sledradar.ai" % page)
            if bs >= 0 and sr >= 0 and sr < bs:
                bad.append("%s: SLED Radar precedes BidStrike in the Products column. "
                           "BidStrike leads every product list (ruled 8/29)" % page)
            if "/construction" in g:
                bad.append("%s: the Products column points INWARD at /construction, "
                           "which was retired to a redirect stub 2026-09-26" % page)
        seen.setdefault(f, []).append(page)
    if len(seen) > 1:
        bad.append("footer differs between pages: %s" % [v for v in seen.values()])
    notes.append("footer sitemap on %d/%d chrome pages" % (sum(len(v) for v in seen.values()), len(CHROME_PAGES)))
    return bad


# --------------------------------------------------------------------------
# 6. The nav must never fold.
# bidstrike-landing shipped a folded nav row on 2026-08-05 by adding one link
# too many; a wrapped nav still looks like it rendered.
#
# RE-RULED 2026-09-26 (holding-company collapse, ruling Q2, which Rodney made
# knowing it reverses this check's first half).
#   OLD assertion: the nav is the site's identity statement and NOT a
#                  placement, so NO bidstrike link may appear in it; link count
#                  identical across pages.
#   NEW assertion: each nav (desktop row AND drawer) carries EXACTLY ONE
#                  BidStrike link, pointing OUT; link count identical across
#                  pages (kept); and the reason the old rule existed is now
#                  measured directly instead of prevented by proxy: in a real
#                  browser layout the desktop row never wraps, clips, overflows
#                  or collides with the header chip, at the narrowest desktop
#                  width and at 1440px, and below the breakpoint the drawer is
#                  reachable and each of its links is one line.
# Why measure: "no bidstrike link" was a proxy for "no fold". The ruling adds
# two links to the row, so the proxy is gone and only the real property is left
# to check. A static count cannot see a fold; only layout can.
#
# HOW IT MEASURES. Chrome headless loads each chrome page from a local server
# (absolute /assets paths need one) with the site's real CSS, real Geist font
# and real script.js, which injects the LinkedIn chip into this same row. A
# probe script appended to the served copy reads getBoundingClientRect after
# document.fonts.ready and writes JSON into the DOM, which --dump-dom returns.
# Nothing on disk is modified. The instrument checks itself first: if the
# viewport width is not the one requested, or Geist did not load, the numbers
# describe a page nobody ships and the check FAILS rather than reporting them.
# If Chrome is missing the check FAILS: a layout check that could not run has
# not passed.
# --------------------------------------------------------------------------
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
NAV_ROW_RE = re.compile(r'<ul class="nav-links">.*?</ul>', re.S)
NAV_DRAWER_RE = re.compile(r'<nav[^>]*\bclass="[^"]*\bsite-nav\b[^"]*".*?</nav>', re.S)

PROBE = r"""<script>
(async function(){
  try { await document.fonts.ready; } catch (e) {}
  await new Promise(function (r) { setTimeout(r, 300); });
  var R = function (el) { var b = el.getBoundingClientRect();
    return {top: b.top, h: b.height, l: b.left, r: b.right}; };
  var out = {iw: innerWidth, docW: document.documentElement.scrollWidth,
             geist: Array.from(document.fonts).some(function (f) {
               return /Geist/.test(f.family) && f.status === "loaded"; })};
  var ul = document.querySelector(".nav-links");
  out.row = ul ? getComputedStyle(ul).display : "missing";
  var tg = document.querySelector(".nav-toggle");
  out.toggle = tg ? getComputedStyle(tg).display : "missing";
  if (ul && out.row !== "none") {
    out.links = [].map.call(ul.querySelectorAll("a"), function (a) {
      var o = R(a); o.t = a.textContent.trim(); o.sw = a.scrollWidth; o.cw = a.clientWidth;
      var cs = getComputedStyle(a); o.lh = parseFloat(cs.lineHeight) || 1.2 * parseFloat(cs.fontSize);
      return o; });
    out.ulSW = ul.scrollWidth; out.ulCW = ul.clientWidth;
    var w = document.querySelector(".nav-wrap");
    out.wrap = R(w);
    out.kids = [].map.call(w.children, function (c) {
      var o = R(c); o.cls = c.className; o.d = getComputedStyle(c).display; return o; });
  } else {
    var nav = document.querySelector(".site-nav");
    if (nav) {
      nav.classList.add("is-open"); document.body.classList.add("nav-menu-open");
      out.drawer = getComputedStyle(nav).display;
      out.dlinks = [].map.call(nav.querySelectorAll("a"), function (a) {
        var o = R(a); o.t = a.textContent.trim(); o.sw = a.scrollWidth; o.cw = a.clientWidth;
      var cs = getComputedStyle(a); o.lh = parseFloat(cs.lineHeight) || 1.2 * parseFloat(cs.fontSize);
      return o; });
      out.navSW = nav.scrollWidth; out.navCW = nav.clientWidth;
    }
  }
  var pre = document.createElement("pre"); pre.id = "__navprobe";
  pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
})();
</script>"""


def _row_breakpoint():
    """The widest width at which .nav-links is display:none, read off the CSS."""
    css = read("styles.css")
    for m in re.finditer(r"@media\s*\(max-width:\s*(\d+)px\)\s*\{(.*?)\n\}", css, re.S):
        if re.search(r"\.nav-links\s*\{\s*display:\s*none", m.group(2)):
            return int(m.group(1))
    return None


def _measure(pages, widths):
    import functools
    import http.server
    import io
    import subprocess
    import threading
    from concurrent.futures import ThreadPoolExecutor

    root = os.getcwd()

    class Probe(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send_head(self):
            path = self.translate_path(self.path)
            if os.path.isdir(path):
                path = os.path.join(path, "index.html")
            if not os.path.exists(path) and os.path.exists(path + ".html"):
                path += ".html"
            if path.endswith(".html") and os.path.exists(path):
                body = read(path).replace("</body>", PROBE + "</body>").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return io.BytesIO(body)
            return super().send_head()

    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Probe, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]

    def one(job):
        page, width = job
        url = "http://127.0.0.1:%d/%s" % (port, page)
        r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                            "--no-first-run", "--window-size=%d,900" % width,
                            "--virtual-time-budget=5000", "--dump-dom", url],
                           capture_output=True, text=True, timeout=90)
        m = re.search(r'<pre id="__navprobe">(.*?)</pre>', r.stdout, re.S)
        return page, width, (json.loads(html.unescape(m.group(1))) if m else None)

    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            return list(ex.map(one, [(p, w) for p in pages for w in widths]))
    finally:
        srv.shutdown()


@check("nav never folds: one outbound bidstrike link per nav, row fits in real layout")
def _():
    bad = []
    counts = set()
    for page in CHROME_PAGES:
        src = read(page)
        row, drawer = NAV_ROW_RE.search(src), NAV_DRAWER_RE.search(src)
        if not row or not drawer:
            bad.append("%s: nav row or drawer not found" % page)
            continue
        for where, blk in (("row", row.group(0)), ("drawer", drawer.group(0))):
            bs = re.findall(r"<a\b[^>]*bidstrike\.cloud[^>]*>", blk)
            if len(bs) != 1:
                bad.append("%s: %s carries %d bidstrike links, ruled exactly 1 "
                           "(2026-09-26)" % (page, where, len(bs)))
            elif 'href="https://bidstrike.cloud/' not in bs[0]:
                bad.append("%s: %s bidstrike link does not point OUT at "
                           "https://bidstrike.cloud" % (page, where))
            counts.add((where, blk.count("<a ")))
    if len({c for w, c in counts if w == "row"}) > 1 or len({c for w, c in counts if w == "drawer"}) > 1:
        bad.append("nav link count differs across pages: %s" % sorted(counts))
    notes.append("nav anchors per page (row, drawer): %s" % sorted(counts))

    # ---- the layout half
    if not os.path.exists(CHROME):
        return bad + ["instrument missing: %s. The layout check could not run, "
                      "and a check that did not run has not passed" % CHROME]
    bp = _row_breakpoint()
    if bp is None:
        return bad + ["could not find the @media rule that hides .nav-links in "
                      "styles.css, so the narrowest desktop width is unknown"]
    # 1024 is below the breakpoint (drawer only), bp+1 is the narrowest width
    # that shows the row and so the one where a fold would appear first, and
    # 1440 is the common laptop width. bp+1 is DERIVED from the CSS so the check
    # follows the breakpoint if it ever moves.
    widths = sorted({1024, bp + 1, 1440})
    notes.append("nav layout widths: %s (row breakpoint derived from CSS: <=%dpx hides it)"
                 % (widths, bp))
    for page, width, m in _measure(CHROME_PAGES, widths):
        tag = "%s @%dpx" % (page, width)
        if m is None:
            bad.append("%s: the layout probe returned nothing. Instrument failure, "
                       "not a pass" % tag)
            continue
        if m["iw"] != width:
            bad.append("%s: viewport measured %dpx, requested %dpx. Instrument "
                       "failure" % (tag, m["iw"], width))
            continue
        if not m["geist"]:
            bad.append("%s: Geist did not load, so this is not the shipped layout" % tag)
            continue
        if m["docW"] > width:
            bad.append("%s: page scrolls sideways (%dpx wide)" % (tag, m["docW"]))
        if width > bp:
            if m["row"] == "none":
                bad.append("%s: desktop nav row is hidden above the breakpoint" % tag)
                continue
            ls = m["links"]
            if not ls:
                bad.append("%s: desktop nav row rendered no links" % tag)
                continue
            tops = {round(l["top"]) for l in ls}
            if len(tops) > 1:
                bad.append("%s: nav row FOLDED onto %d lines: %s" % (
                    tag, len(tops), [(l["t"], round(l["top"])) for l in ls]))
            if max(l["h"] for l in ls) - min(l["h"] for l in ls) >= min(l["lh"] for l in ls) / 2:
                bad.append("%s: a nav label wrapped (heights differ by half a line or more): %s" % (
                    tag, [(l["t"], round(l["h"])) for l in ls]))
            for l in ls:
                if l["sw"] > l["cw"] + 1:
                    bad.append("%s: nav link %r is clipped (%d of %dpx)" % (
                        tag, l["t"], l["cw"], l["sw"]))
            if m["ulSW"] > m["ulCW"] + 1:
                bad.append("%s: nav row overflows its box (%d > %dpx)" % (
                    tag, m["ulSW"], m["ulCW"]))
            vis = [k for k in m["kids"] if k["d"] != "none" and k["h"] > 0]
            if m["wrap"]["h"] > max(k["h"] for k in vis) + 1:
                bad.append("%s: header row is %.0fpx tall, taller than its tallest "
                           "item (%.0fpx), so it wrapped" % (
                               tag, m["wrap"]["h"], max(k["h"] for k in vis)))
            first, last = min(l["l"] for l in ls), max(l["r"] for l in ls)
            # any other visible header item (brand lockup, the JS-injected
            # LinkedIn chip, the toggle) that overlaps the row's span collides
            for k in vis:
                if "nav-links" in k["cls"].split():
                    continue
                if k["l"] < last - 1 and k["r"] > first + 1:
                    bad.append("%s: nav row (%.0f-%.0fpx) collides with %r (%.0f-%.0fpx)"
                               % (tag, first, last, k["cls"] or "?", k["l"], k["r"]))
            notes.append("%s: 1 row, %d links, %.0fpx to %.0fpx, header row %.0fpx tall, "
                         "nearest item right of it starts %s"
                         % (tag, len(ls), first, last, m["wrap"]["h"],
                            next(("%.0fpx (%s)" % (k["l"], k["cls"]) for k in
                                  sorted(vis, key=lambda k: k["l"]) if k["l"] >= last - 1),
                                 "none")))
        else:
            if m["row"] != "none":
                bad.append("%s: desktop row still showing below the breakpoint" % tag)
            if m["toggle"] in ("none", "missing"):
                bad.append("%s: menu toggle hidden below the breakpoint, so this width "
                           "has NO navigation" % tag)
            dl = m.get("dlinks") or []
            if m.get("drawer") in (None, "none") or not dl:
                bad.append("%s: drawer did not open" % tag)
                continue
            # A wrapped label is taller by a whole LINE. Exact equality is the
            # wrong instrument: .site-nav a:last-child drops its bottom border,
            # so the last row is 1px shorter on a perfectly good drawer (it
            # false-failed exactly that way the first time this ran, 2026-09-26).
            if max(l["h"] for l in dl) - min(l["h"] for l in dl) >= min(l["lh"] for l in dl) / 2:
                bad.append("%s: a drawer label wrapped (heights differ by half a line or more): %s" % (
                    tag, [(l["t"], round(l["h"])) for l in dl]))
            if m["navSW"] > m["navCW"] + 1:
                bad.append("%s: drawer overflows sideways" % tag)
            notes.append("%s: drawer opens, %d links, each %s px tall"
                         % (tag, len(dl), sorted({round(l["h"]) for l in dl})))
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

    # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
    #   OLD assertion: a ProfessionalService node exists and lists
    #                  https://bidstrike.cloud in sameAs.
    #   NEW assertion: an Organization node with the site's #organization @id
    #                  exists and lists https://bidstrike.cloud in sameAs, and NO
    #                  ProfessionalService node remains.
    # Why: SRS sells no services now. ProfessionalService would tell every search
    # engine the opposite of the ruling, on the placement nobody sees on screen.
    # The sameAs link and the SoftwareApplication checks below are unchanged, and
    # the publisher @id they point at is now required to exist on the org node.
    org = next((b for b in parsed if b.get("@type") == "Organization"), None)
    app = next((b for b in parsed if b.get("@type") == "SoftwareApplication"
                and b.get("url") == "https://bidstrike.cloud"),
               next((b for b in parsed if b.get("@type") == "SoftwareApplication"), None))

    if any(b.get("@type") == "ProfessionalService" for b in parsed):
        bad.append("a ProfessionalService node is back. SRS sells no services "
                   "since 2026-09-26; the node is an Organization")
    if org is None:
        bad.append("Organization node missing")
    else:
        if org.get("@id") != "https://smithrevenuestrategy.com/#organization":
            bad.append("Organization @id is %r, which the SoftwareApplication "
                       "publisher references" % org.get("@id"))
        # RE-RULED AGAIN 2026-09-26 (Rodney approved the fix). schema.org sameAs means
        # "this is the same thing", and a product SRS OWNS is not SRS. That claim also
        # contradicts the prior-IP position (SRS, LLC owns the products as assets).
        #   OLD: bidstrike.cloud MUST be in Organization sameAs.
        #   NEW: no product domain may be in Organization sameAs; the org-to-product
        #        link is carried by each SoftwareApplication's publisher @id (checked below).
        for dom in ("bidstrike.cloud", "sledradar.ai"):
            if any(dom in u for u in org.get("sameAs", [])):
                bad.append("%s is in Organization sameAs; a product is not the same "
                           "entity as its owner. Link it via publisher @id" % dom)

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
@check("all placements present on their expected pages")
def _():
    # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
    #   OLD assertion: six named placements, including index bs-band/home-band,
    #                  work-together-paths, results bs-case/results-case and the
    #                  is-this-you "The bid desk" card.
    #   NEW assertion: the placements on the five live pages (index
    #                  home-products, about built-tray/about-tray, faq, contact,
    #                  plus the site-wide nav and footer), AND every page that
    #                  used to carry a placement but was retired is a DECLARED
    #                  chromeless noindex stub, not a live page that quietly lost
    #                  its placement.
    # Why: work-together, results and is-this-you were retired to redirect stubs
    # by the ruling, and the homepage band became the two-product card row. The
    # retired half is not deleted, it is inverted: if one of those pages comes
    # back to life, this check demands the ruling be revisited rather than
    # passing a live page with nothing on it.
    retired = ["work-together.html", "results.html", "is-this-you.html"]
    expected = {
        "index.html": ["solution-chip", "utm_campaign=home-products"],
        "contact.html": ["utm_campaign=contact"],
        "about.html": ["built-tray", "utm_campaign=about-tray"],
        # The card marker was renamed situation_c -> bid_desk on 2026-08-30:
        # "situation_c" told a reader nothing about what they were reading.
        # This assertion is about the CARD still existing, so it follows the
        # rename rather than pinning the old opaque label.
        # RENAMED AGAIN 2026-08-31: bid_desk -> "The bid desk", when Rodney
        # retired the terminal-coder register site-wide. Same reasoning as the
        # 8/30 move, one step further: a snake_case marker was still code-speak
        # wearing a label's clothes. The needle follows the copy, by design.
        # NOTE the utm_campaign value is DELIBERATELY unchanged - it is a live
        # attribution key, and renaming a visible label is not a reason to break
        # historical campaign data.
        # RETIRED 2026-09-26 with the page: "is-this-you.html": ["The bid desk",
        # "utm_campaign=is-this-you"]. See `retired` above.
        "faq.html": ["utm_campaign=faq"],
    }
    bad = []
    for page, needles in expected.items():
        src = read(page)
        for needle in needles:
            if needle not in src:
                bad.append("%s: missing %r" % (page, needle))
    for page in CHROME_PAGES:
        src = read(page)
        for name in ("nav", "footer"):
            if "utm_campaign=%s" % name not in src:
                bad.append("%s: missing the site-wide %r placement" % (page, name))
    for page in retired:
        if not os.path.exists(page):
            bad.append("%s: gone entirely; it was retired to a redirect stub so "
                       "inbound links do not 404" % page)
        elif page in CHROME_PAGES:
            bad.append("%s: is a live chrome page again but was retired 2026-09-26 "
                       "with its placement. Revisit the ruling" % page)
        elif "bidstrike.cloud" in read(page):
            bad.append("%s: a retired stub still carries a bidstrike placement" % page)
    return bad


# --------------------------------------------------------------------------
# 9. Ownership disclosure. BidStrike is Rodney's own company, not a partner
# referral. The /about tray sits directly under a tray whose closing line
# describes revenue-share referrals, so the distinction has to be explicit.
# --------------------------------------------------------------------------
@check("ownership disclosed on /about and /")
def _():
    # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
    #   OLD assertion: the /about built-tray says "own BidStrike outright", and
    #                  results.html says "my own product".
    #   NEW assertion: the /about built-tray says "Smith Revenue Strategy owns
    #                  both products" AND keeps "Neither is a partner referral";
    #                  the homepage says "Smith Revenue Strategy is a holding
    #                  company. It owns two software products" (the approved
    #                  brand paragraph, _ops/rules/srs-holding-company-positioning.md).
    # Why: the owner is now the company, not Rodney personally, and there are two
    # products, so the old phrase is no longer the true statement. /results was
    # retired; its half of this check moves to the homepage, which now carries
    # the ownership statement in the brand paragraph. The partner-referral line is
    # asserted because it is the distinction this check was written to protect.
    bad = []
    about = read("about.html")
    tray = about.split('id="built-tray"', 1)
    if len(tray) < 2:
        bad.append("about.html: built-tray missing")
    else:
        body = re.sub(r"\s+", " ", tray[1].split("</details>", 1)[0])
        if "Smith Revenue Strategy owns both products" not in body:
            bad.append("about.html: built-tray does not state that Smith Revenue "
                       "Strategy owns both products")
        if "Neither is a partner referral" not in body:
            bad.append("about.html: built-tray lost the partner-referral distinction")
    home = re.sub(r"\s+", " ", read("index.html"))
    if ("Smith Revenue Strategy is a holding company. It owns two software products"
            not in home):
        bad.append("index.html: the brand paragraph no longer states ownership")
    return bad


# --------------------------------------------------------------------------
# 11. The header wordmark is site-wide, like the footer, so it drifts the same
# way. The lockup art is the SRS glyph only; these two strings are the company
# name and tagline that used to live inside the logo image, so they have to
# match the brand exactly and appear on every page.
# --------------------------------------------------------------------------
@check("header wordmark present and identical on all pages")
def _():
    # children are <strong>/<small>, NOT nested spans, so the first </span>
    # closes the block
    block = re.compile(r'<span class="brand-words".*?</span>', re.S)
    bad = []
    seen = {}
    for page in CHROME_PAGES:
        m = block.search(read(page))
        if not m:
            bad.append("%s: no brand-words block" % page)
            continue
        seen.setdefault(m.group(0), []).append(page)
        if 'aria-hidden="true"' not in m.group(0):
            bad.append("%s: brand-words must be aria-hidden (the brand link "
                       "already carries the accessible name)" % page)
    if len(seen) > 1:
        bad.append("brand-words differs between pages: %s" % [v for v in seen.values()])
    # The tagline was "Unlock AI-Enabled Growth" until 2026-08-28. Rodney ruled
    # the lockup carries the ruled headline instead, so one message runs
    # everywhere. Assert the NEW literal - never delete this check, or the
    # tagline silently drifts back page by page.
    for text in ("Smith Revenue Strategy", "Freedom for the work only people can do."):
        if not any(text in b for b in seen):
            bad.append("brand-words missing the string %r" % text)
    notes.append("brand-words on %d/%d chrome pages" % (sum(len(v) for v in seen.values()), len(CHROME_PAGES)))
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
# 11. The wordmark is the real logo art, never type faking it.
# Until 2026-08-12 every display use of the name was `<span class="bs-mark">
# Bid<i>Strike</i></span>` - Inter in bold italic with the "Strike" half tinted
# lime. It approximated the logo and matched it nowhere: wrong letterforms,
# wrong slant, and no strike blade at all. The art now ships instead. This
# check exists so nobody reintroduces the text stand-in one placement at a
# time, and so the img keeps the alt text that carries the name to screen
# readers and search once the word itself is gone from the markup.
# --------------------------------------------------------------------------
# 2026-08-19: the site inverted from a DARK theme to the light BidStrike-family
# theme, so the correct art in the MARKUP flipped. The dark-ink cut is now the
# default because most surfaces are light; the two navy islands (.bs-band and the
# footer) swap to the white cut in CSS via `content: url()`, and the lime CTA
# keeps the dark art via a more-specific override. This gate asserts the MARKUP
# default only - it cannot see the CSS swap, so do not "fix" a navy surface by
# changing its <img src>.
# Before this date the expectation was bidstrike-logo-white.png, which was right
# for the dark site and became a stale assertion the moment the theme changed.
LOGO_SRC = "/assets/images/brand/bidstrike-logo.png"
# The ON-BUTTON variant, added 2026-08-29. .bs-cta is a LIME button and the
# BidStrike strike is lime (mean 185,250,14 against --lime #aef23f), so on that
# fill the strike all but disappears. This asset is the same art with a shadow
# composited behind THE STRIKE PIXELS ONLY - the navy wordmark casts nothing.
#
# It is allowed in exactly one place: inside a .bs-cta anchor. Anywhere else is
# a FAIL, because a shadowed mark on a flat ground is just a dirty edge. That
# makes this assertion narrower than the one it replaced, not looser.
LOGO_SRC_BUTTON = "/assets/images/brand/bidstrike-logo-onbutton.png"


@check("every display wordmark is the logo art, with alt text")
def _():
    bad = []
    css = read("styles.css")

    if ".bs-mark" in css:
        bad.append("styles.css still defines .bs-mark (the type stand-in)")

    found = 0
    per_page = {}
    for page in PAGES:
        src = read(page)
        # any <img> of the BidStrike art counts as a lockup placement, classed
        # bs-logo or not (the homepage card carries it without the class)
        per_page[page] = len([t for t in re.findall(r"<img\b[^>]*>", src)
                              if "/brand/bidstrike-logo" in t])
        if "bs-mark" in src:
            bad.append("%s: still renders the .bs-mark type stand-in" % page)
        # which placements sit inside a lime CTA button
        cta_blocks = " ".join(re.findall(r'<a class="bs-cta"[^>]*>.*?</a>', src, re.S))
        for tag in re.findall(r"<img\b[^>]*\bbs-logo\b[^>]*>", src):
            found += 1
            attrs = dict(ATTR_RE.findall(tag))
            on_button = tag in cta_blocks
            want = LOGO_SRC_BUTTON if on_button else LOGO_SRC
            if attrs.get("src") != want:
                bad.append("%s: bs-logo src is %r, expected %r (%s a .bs-cta button)"
                           % (page, attrs.get("src"), want,
                              "inside" if on_button else "not inside"))
            if attrs.get("alt") != "BidStrike":
                bad.append('%s: bs-logo alt is %r, expected "BidStrike" - the '
                           "brand name only reaches a screen reader through alt "
                           "now that the text is gone" % (page, attrs.get("alt")))
            if not (attrs.get("width") and attrs.get("height")):
                bad.append("%s: bs-logo has no width/height, so the row reflows "
                           "when the art loads" % page)

    # The art file has to exist and match the attributes, or every placement
    # renders at the wrong aspect (or as a broken-image icon).
    if not os.path.exists(LOGO_SRC_BUTTON.lstrip("/")):
        bad.append("the on-button art %s is missing" % LOGO_SRC_BUTTON)
    if not os.path.exists(LOGO_SRC.lstrip("/")):
        bad.append("missing asset %s" % LOGO_SRC)
    else:
        with open(LOGO_SRC.lstrip("/"), "rb") as fh:
            head = fh.read(33)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            bad.append("%s is not a PNG" % LOGO_SRC)
        else:
            w, h = struct.unpack(">II", head[16:24])
            # 2026-08-19: this compared the PNG against a HARDCODED (640, 108).
            # That is a snapshot, not an invariant - it went stale the moment the
            # light-theme restyle swapped the white cut for the dark one, and it
            # would go stale again on any future art change. What actually matters
            # is that the intrinsic size DECLARED IN THE MARKUP matches the real
            # file, because a mismatch is what causes cumulative layout shift.
            # So: read the declared dims off the pages and compare to the file.
            declared = set()
            for _pg in PAGES:
                with open(_pg, encoding="utf-8") as _fh:
                    _src = _fh.read()
                for _tag in re.findall(r"<img[^>]*>", _src):
                    if LOGO_SRC not in _tag:
                        continue
                    _mw = re.search(r'width="(\d+)"', _tag)
                    _mh = re.search(r'height="(\d+)"', _tag)
                    if _mw and _mh:
                        declared.add((int(_mw.group(1)), int(_mh.group(1))))
            if not declared:
                bad.append("no <img> declares width/height for %s" % LOGO_SRC)
            elif len(declared) > 1:
                bad.append("%s is declared at %d different sizes across the site: %s"
                           % (LOGO_SRC, len(declared), sorted(declared)))
            elif declared != {(w, h)}:
                d = sorted(declared)[0]
                bad.append("%s is %dx%d but the markup declares %dx%d "
                           "(intrinsic-size mismatch causes layout shift)"
                           % (LOGO_SRC, w, h, d[0], d[1]))

    notes.append("bs-logo placements: %d across %d pages" % (found, len(PAGES)))
    # The floor was 13 from 2026-08-12: one lockup per chrome page, and all but
    # one of those was the .bs-footer-block chip. Rodney retired that chip on
    # 2026-08-30 when the footer became the sitemap, so 13 is no longer a
    # reachable number and holding it would fail forever on a shipped ruling.
    #
    # The floor is NOT deleted. It is re-derived from what the design now says
    # should exist: the named campaign placements in check 8, each of which
    # carries a lockup. Falling below that still means a placement went missing.
    #
    # RE-RULED 2026-09-26 (holding-company collapse, ruling Q2).
    #   OLD assertion: at least 5 bs-logo placements site-wide.
    #   NEW assertion: each page in LOCKUP_PAGES carries at least one img of the
    #                  BidStrike art, and every such img passes the src/alt/size
    #                  checks above, bs-logo class or not.
    # Why: the five came from placements on /results, /work-together,
    # /is-this-you and the old home band, all retired. A bare total can be met by
    # stacking logos on one page while another placement loses its lockup, so the
    # floor is now pinned per placement. The nav, footer and contact placements
    # are text by design and are not in the list.
    LOCKUP_PAGES = {"index.html": "home-products card",
                    "about.html": "about-tray",
                    "faq.html": "faq answer"}
    for page, what in LOCKUP_PAGES.items():
        if not per_page.get(page):
            bad.append("%s: the %s placement lost its BidStrike lockup art" % (page, what))
    # the src/alt/size checks above only see imgs classed bs-logo; hold the
    # unclassed ones to the same standard
    for page in PAGES:
        for tag in re.findall(r"<img\b[^>]*>", read(page)):
            if "/brand/bidstrike-logo" not in tag or re.search(r"\bbs-logo\b", tag):
                continue
            attrs = dict(ATTR_RE.findall(tag))
            if attrs.get("src") != LOGO_SRC:
                bad.append("%s: BidStrike art src is %r, expected %r"
                           % (page, attrs.get("src"), LOGO_SRC))
            if attrs.get("alt") != "BidStrike":
                bad.append('%s: BidStrike art alt is %r, expected "BidStrike"'
                           % (page, attrs.get("alt")))
            if not (attrs.get("width") and attrs.get("height")):
                bad.append("%s: BidStrike art has no width/height" % page)
    notes.append("bidstrike lockup art per page: %s"
                 % {p: n for p, n in per_page.items() if n})
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
