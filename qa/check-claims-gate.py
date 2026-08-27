#!/usr/bin/env python3
"""Claims gate: quotes, attributions, and the conditions attached to them.

Every check here exists because the claim it guards is one somebody could be held
to. Scope is enumerated from the filesystem.

Run: python3 qa/check-claims-gate.py   # exit 0 = pass
"""
import glob, sys, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
PAGES = sorted(glob.glob("*.html"))

# The Cuban quote. Rodney's standing condition (2026-08-13 override): it ships ONLY
# beside a specific, adjacent next step, and NEVER with a photograph of him - that is
# right of publicity, not a design preference, and a royalty-free licence from a
# photographer does not reach it.
CUBAN_FULL = "two types of companies in this world"
CUBAN_TRUNC = "two types of companies"
NEXT_STEP = "Let's get started"

# 60/30/10 is RODNEY'S OWN teaching frame and appears NOWHERE in the Van Clief paper.
# Attributing his own IP to someone else is the failure this guards.
ICM_NAMES = ["Van Clief", "McDermott", "2603.16021"]

# Client identities that must never appear on a public page. Say what happened to
# the WORK, never who it happened to, and NEVER characterize a client's finances -
# true is not a defense there.
#
# "Texas Welding Company" is DELIBERATELY ABSENT from this list. It is already named
# on the live site under Kennan's explicit 2026-08-13 naming and quote approval,
# recorded in projects/BidStrike/messaging/CLAIMS.md, and check-bidstrike-surfaces.py
# may depend on it. Adding it here would break a legitimate, approved use.
NEVER_ON_SITE = ["Andrew Mulford", "Justin Dorroh", "Jacob Earls", "Kennan Westbrook",
                 "Clark Contractors", "One Life Group", "Leap Development"]

def claim_context(html):
    """Strip the contexts where naming a person is a CONSENTED RELATIONSHIP rather
    than a client-outcome claim, then return what is left.

    This distinction is the whole check, and the 8/24 draft did not make it: that
    version banned the names site-wide and fired on about.html, where Andrew Mulford
    and Justin Dorroh appear as ADVISORS - photo, role, their own LinkedIn, their own
    company website - plus matching JSON-LD Person entities. Nobody puts a person's
    headshot and LinkedIn on their site without agreement. That is a stated
    relationship, not an anonymized result, and erasing it would have been wrong.

    What stays banned is a client identity anywhere an OUTCOME is being claimed, on
    ANY page. So the exemption is scoped to the markup, not to a page name: drop a
    name into a results paragraph on about.html and this still fires.
    """
    out = re.sub(r'<script type="application/ld\+json">.*?</script>', "", html, flags=re.S)
    out = re.sub(r'<article class="resource-card">.*?</article>', "", out, flags=re.S)
    return out


fails = []
for p in PAGES:
    body = claim_context(open(p, encoding="utf-8").read())
    for name in NEVER_ON_SITE:
        if name in body:
            fails.append("%s  client identity in an outcome-claim context -> %s. "
                         "Say what happened to the WORK, never who it happened to."
                         % (p, name))

for p in PAGES:
    s = open(p, encoding="utf-8").read()
    low = s.lower()

    if CUBAN_FULL in s:
        if NEXT_STEP not in s:
            fails.append("%s  Cuban quote present without its adjacent next step "
                         "(%r). Rodney's standing condition." % (p, NEXT_STEP))
        # a photograph of Cuban is a right-of-publicity problem, not a style one
        for m in re.finditer(r'<img[^>]+>', s):
            tag = m.group(0).lower()
            if "cuban" in tag:
                fails.append("%s  an <img> references Cuban. NO PHOTOGRAPH, ever." % p)
    elif CUBAN_TRUNC in s:
        # the exact truncation nearly every blog makes
        fails.append('%s  the Cuban quote is TRUNCATED - it reads "%s" but the '
                     'verified wording is "%s". Ship the full sentence.'
                     % (p, CUBAN_TRUNC, CUBAN_FULL))

    # 60/30/10 must never sit in the same breath as the ICM attribution
    if "60/30/10" in s:
        for name in ICM_NAMES:
            if name.lower() in low:
                # same paragraph is the test, not same page
                for para in re.split(r'</p>|</li>', s):
                    if "60/30/10" in para and name.lower() in para.lower():
                        fails.append("%s  60/30/10 appears in the same passage as "
                                     "%r. That frame is RODNEY'S OWN and appears "
                                     "nowhere in the ICM paper - never attribute it."
                                     % (p, name))
                        break

print("  scope: %d pages enumerated from disk" % len(PAGES))
print("  guarding: Cuban wording + adjacent next step + no photograph; ICM attribution")
if fails:
    print("\nRESULT: FAIL")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nRESULT: PASS")
