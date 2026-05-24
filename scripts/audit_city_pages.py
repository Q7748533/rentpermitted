#!/usr/bin/env python3
"""Post-generation audit for pSEO city pages. Run after generate_pages.py.
Checks: tag balance, em-dashes, HTML escaping, GEO block coverage, TOC links, empty sections.
Usage: python3 scripts/audit_city_pages.py [pages_dir]"""

import os, re, glob, sys

PAGES_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# Find all city page HTML (state/city/index.html pattern)
city_pages = sorted(glob.glob(f"{PAGES_DIR}/*/*/index.html"))
if not city_pages:
    print("ERROR: No city pages found (expected */*/index.html pattern)")
    sys.exit(1)

errors = []
warnings = []
geo_stats = {"digest": 0, "key-stats": 0, "enforcement-note": 0, "bottom-line": 0}

for filepath in city_pages:
    rel = os.path.relpath(filepath, PAGES_DIR)
    with open(filepath) as f:
        html = f.read()

    # 1. Tag balance
    for tag in ['section', 'div', 'article', 'main', 'blockquote', 'details', 'summary']:
        opens = len(re.findall(f'<{tag}[ >]', html))
        closes = len(re.findall(f'</{tag}>', html))
        if opens != closes:
            errors.append(f"{rel}: <{tag}> unbalanced ({opens}/{closes})")

    # 2. Em-dashes zero tolerance (en-dashes in numeric ranges OK per em-dash-removal-pattern)
    dc = html.count('\u2014')  # em-dash only
    if dc > 0:
        errors.append(f"{rel}: {dc} em-dashes")

    # 3. Unescaped & in visible content (not <script>, not URL attrs)
    body_match = re.search(r'<body>(.*?)</body>', html, re.DOTALL)
    if body_match:
        body = body_match.group(1)
        body_no_scripts = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
        raw_amps = re.findall(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#[xX][0-9a-fA-F]+);)', body_no_scripts)
        for amp in raw_amps:
            pos = body_no_scripts.find(amp)
            ctx = body_no_scripts[max(0,pos-15):pos+25].strip()
            if 'href=' not in ctx[:60] and 'src=' not in ctx[:60]:
                errors.append(f"{rel}: unescaped & → ...{ctx}...")

    # 4. GEO quotable unit coverage
    if 'class="digest"' in html:
        geo_stats["digest"] += 1
    else:
        errors.append(f"{rel}: missing Regulation Digest")
    if 'class="key-stats"' in html:
        geo_stats["key-stats"] += 1
    else:
        errors.append(f"{rel}: missing Key Numbers")
    if 'class="enforcement-note"' in html:
        geo_stats["enforcement-note"] += 1
    if 'class="bottom-line"' in html:
        geo_stats["bottom-line"] += 1
    else:
        errors.append(f"{rel}: missing Bottom Line")

    # 5. TOC id matching
    toc_match = re.search(r'<nav class="toc".*?</nav>', html, re.DOTALL)
    if toc_match:
        toc = toc_match.group(0)
        toc_hrefs = re.findall(r'href="#([^"]+)"', toc)
        for href in toc_hrefs:
            if f'id="{href}"' not in html:
                warnings.append(f"{rel}: TOC #{href} has no matching id")

    # 6. Empty GEO blocks
    for bc in ['digest', 'key-stats', 'enforcement-note', 'bottom-line']:
        pattern = f'<section class="{bc}">'
        if pattern in html:
            start = html.find(pattern)
            end = html.find('</section>', start)
            block = html[start:end]
            text = re.sub(r'<[^>]*>', '', block).strip()
            h2m = re.search(r'<h2[^>]*>(.*?)</h2>', block)
            if h2m:
                text = text.replace(h2m.group(1), '').strip()
            if not text or len(text) < 5:
                errors.append(f"{rel}: empty GEO block '{bc}'")

# Report
n = len(city_pages)
print(f"Pages: {n}")
print(f"Errors: {len(errors)}  Warnings: {len(warnings)}")
print(f"GEO: digest={geo_stats['digest']}/{n} key-stats={geo_stats['key-stats']}/{n} "
      f"enforcement={geo_stats['enforcement-note']}/{n} bottom-line={geo_stats['bottom-line']}/{n}")

if errors:
    print(f"\n=== ERRORS ({len(errors)}) ===")
    for e in errors:
        print(f"  ❌ {e}")
if warnings:
    print(f"\n=== WARNINGS ({len(warnings)}) ===")
    for w in warnings:
        print(f"  ⚠️ {w}")

if not errors and not warnings:
    print("\n✅ ALL CLEAN")
    sys.exit(0)
elif not errors:
    print(f"\n⚠️ {len(warnings)} warnings only — review before deploy")
    sys.exit(0)
else:
    print(f"\n🔴 {len(errors)} errors — DO NOT DEPLOY")
    sys.exit(1)
