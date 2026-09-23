#!/usr/bin/env python3
"""Fetches and runs the canonical SRS voice gate from srs-brand.

Deliberately NOT a copy. A vendored gate stops covering the day the real one
changes, and it keeps reporting a pass while it does. Rules live in
https://github.com/Smith-Revenue-Strategy-LLC/srs-brand/blob/main/gates/check-voice-core.py

    python3 qa/check-voice.py [paths...]      # default: public/
"""
import pathlib, runpy, subprocess, sys, tempfile, urllib.request

RAW = ("https://raw.githubusercontent.com/Smith-Revenue-Strategy-LLC/"
       "srs-brand/main/gates/check-voice-core.py")


def fetch(dest):
    try:
        with urllib.request.urlopen(RAW, timeout=15) as r:
            dest.write_bytes(r.read())
        return "https"
    except Exception:
        pass
    # Private repo, or no network. Fall back to the GitHub CLI, which carries auth.
    try:
        out = subprocess.run(
            ["gh", "api", "repos/Smith-Revenue-Strategy-LLC/srs-brand/contents/"
             "gates/check-voice-core.py", "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, check=True).stdout
        dest.write_bytes(out)
        return "gh"
    except Exception as e:
        sys.exit(f"check-voice: could not fetch the canonical gate ({e}).\n"
                 "  This is a FAILURE, not a skip. A gate that cannot load has not passed.")


args = sys.argv[1:] or ["."]
with tempfile.TemporaryDirectory() as d:
    g = pathlib.Path(d) / "check-voice-core.py"
    how = fetch(g)
    print(f"check-voice: canonical gate fetched via {how}")
    sys.argv = [str(g)] + args
    runpy.run_path(str(g), run_name="__main__")
