#!/usr/bin/env python3
"""Generate sitemap.xml from the pages actually on disk.

Scope is ENUMERATED, never hand-maintained, so a new page cannot silently fall
out of the sitemap while the file keeps looking correct.
Run from the repo root: python3 qa/build-sitemap.py
"""
import glob, os, datetime, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
BASE = "https://smithrevenuestrategy.com"
# priority by page role; anything unlisted gets the default
PRIORITY = {"index.html": "1.0", "sled-radar.html": "0.9", "work-together.html": "0.9",
            "results.html": "0.8", "about.html": "0.8", "contact.html": "0.8",
            "faq.html": "0.7", "events.html": "0.7", "is-this-you.html": "0.6",
            "privacy.html": "0.3"}
today = datetime.date.today().isoformat()

pages = sorted(glob.glob("*.html"))
if not pages:
    print("FATAL: no pages found"); sys.exit(1)

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemap.org/schemas/sitemap/0.9">'.replace("sitemap.org", "sitemaps.org")]
for p in pages:
    slug = "" if p == "index.html" else "/" + p[:-5]   # clean URLs, GitHub Pages resolves them
    out.append("  <url>")
    out.append("    <loc>%s%s</loc>" % (BASE, slug if slug else "/"))
    out.append("    <lastmod>%s</lastmod>" % today)
    out.append("    <priority>%s</priority>" % PRIORITY.get(p, "0.5"))
    out.append("  </url>")
out.append("</urlset>")

open("sitemap.xml", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("sitemap.xml written with %d urls (enumerated from disk):" % len(pages))
for p in pages:
    print("   ", p)
