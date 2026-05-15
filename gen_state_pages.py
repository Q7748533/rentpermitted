#!/usr/bin/env python3
"""RentPermitted State Hub Page Generator — groups cities by state, generates hub pages."""
import json, os, html

BASE = "/home/ubuntu/rentpermitted"
with open("/tmp/cities_batch1.json") as f:
    city_data = json.load(f)

STATES = {}
for slug, d in city_data.items():
    s = d["state"]
    if s not in STATES:
        STATES[s] = {"abbr": d["state_abbr"], "cities": []}
    STATES[s]["cities"].append({**d, "slug": slug})

def state_slug(state_name):
    return state_name.lower().replace(" ", "-")

def state_overview(state_name, cities):
    """Generate a state-level regulatory overview from city data."""
    n = len(cities)
    archetypes = set(c.get("archetype", "guide") for c in cities)
    statuses = [c.get("status_label", "Licensed") for c in cities]
    fees = [c["fee_amount"] for c in cities]

    # Determine state-level tone
    if all(a == "warning" for a in archetypes):
        tone = "restrictive"
        overview = (
            f"{state_name} has some of the most restrictive short-term rental regulations in the country. "
            f"Across all {n} cities we track, investors face significant barriers including primary residence requirements, "
            f"night caps, and active enforcement. STR operators must research city-level rules carefully before investing."
        )
    elif all(a == "opportunity" for a in archetypes):
        tone = "favorable"
        overview = (
            f"{state_name} stands out as an STR-friendly state with regulatory clarity and investor protections. "
            f"Across all {n} cities we track, reasonable fees, clear rules, and state-level preemption laws "
            f"make this one of the most predictable markets for short-term rental investment."
        )
    elif any(a == "opportunity" for a in archetypes) and any(a == "warning" for a in archetypes):
        tone = "mixed"
        overview = (
            f"{state_name} presents a mixed regulatory landscape — some cities welcome STR investment while others impose strict limits. "
            f"Investors must choose cities carefully. Across {n} cities we cover, the rules range from "
            f"light-touch registration to primary residence mandates and night caps."
        )
    else:
        tone = "moderate"
        overview = (
            f"{state_name} maintains a moderate approach to short-term rental regulation. "
            f"Across {n} cities we track, most require registration and compliance with local rules, "
            f"but outright bans are rare. Investors should verify city-specific requirements before purchasing."
        )

    # State preemption notes
    preemption = ""
    if state_name == "Arizona":
        preemption = "\n\nArizona's SB1350 prohibits cities from banning short-term rentals outright, providing strong state-level protection for investors. Cities can require licenses and enforce nuisance rules, but cannot restrict STRs by zoning alone."
    elif state_name == "Texas":
        preemption = "\n\nTexas has no state-level STR preemption law, but most major cities (Austin, Dallas, Houston) have adopted straightforward registration systems rather than restrictive caps."
    elif state_name == "Florida":
        preemption = "\n\nFlorida preempts local governments from banning vacation rentals entirely (FL Stat. 509.032), but cities retain authority over registration, fees, and enforcement."

    return overview + preemption

def city_comparison_table(cities):
    """Generate a comparison table of all cities in a state."""
    rows = ""
    for c in sorted(cities, key=lambda x: x["city"]):
        status = c.get("status_label", "Unknown")
        fee = c["fee_amount"][:80]
        archetype = c.get("archetype", "guide")
        badge_color = "var(--red)" if archetype == "warning" else ("var(--green)" if archetype == "opportunity" else "var(--orange)")
        row = (
            f'      <tr>'
            f'<td><a href="/{c["slug"]}/"><strong>{html.escape(c["city"])}</strong></a></td>'
            f'<td><span class="mini-badge" style="background:{badge_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8rem">{html.escape(status)}</span></td>'
            f'<td class="fee-cell">{html.escape(fee)}</td>'
            f'</tr>\n'
        )
        rows += row
    return f'''<div class="table-responsive"><table class="state-table">
      <thead><tr><th>City</th><th>Status</th><th>License Fee</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def risk_ranking(cities):
    """Generate a ranked list from most restrictive to most investor-friendly."""
    scored = []
    for c in cities:
        score = 0
        a = c.get("archetype", "guide")
        status = c.get("status_label", "")
        if a == "warning":
            score = 3
        elif a == "guide":
            score = 2
        else:
            score = 1
        # Penalize: primary residence + caps
        if "primary residence" in status.lower():
            score += 2
        if "cap" in status.lower():
            score += 1
        if "ban" in status.lower() or "only" in status.lower():
            score += 2
        scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    items = ""
    for i, (score, c) in enumerate(scored):
        level = "🔴 High barrier" if score >= 5 else ("🟡 Moderate" if score >= 3 else "🟢 Accessible")
        items += f'        <li><strong>{html.escape(c["city"])}</strong> — {level}: {html.escape(c.get("verdict","")[:100])}</li>\n'
    return f'''<h2 id="risk-ranking">Regulatory Risk Ranking</h2>
    <p>From most restrictive to most investor-friendly within {cities[0]["state"]}:</p>
    <ol class="risk-list">
{items}    </ol>'''

def gen_state_schema(state_name, state_abbr, state_slug, cities, title, desc):
    """Generate JSON-LD schema for state hub page."""
    n = len(cities)
    city_names = ", ".join(c["city"] for c in sorted(cities, key=lambda x: x["city"]))
    return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "Article",
      "@id": "https://www.rentpermitted.com/{state_slug}/#article",
      "headline": "{title}",
      "description": "{desc[:200].replace(chr(34), '')}",
      "datePublished": "2026-05-15",
      "dateModified": "2026-05-15",
      "author": {{"@id": "https://www.rentpermitted.com/#organization"}},
      "publisher": {{"@id": "https://www.rentpermitted.com/#organization"}},
      "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://www.rentpermitted.com/{state_slug}/"}},
      "about": {{"@type": "Thing", "name": "{state_name} short-term rental regulations"}},
      "isAccessibleForFree": true
    }},
    {{
      "@type": "BreadcrumbList",
      "@id": "https://www.rentpermitted.com/{state_slug}/#breadcrumb",
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.rentpermitted.com/"}},
        {{"@type": "ListItem", "position": 2, "name": "{state_name}", "item": "https://www.rentpermitted.com/{state_slug}/"}}
      ]
    }},
    {{
      "@type": "FAQPage",
      "@id": "https://www.rentpermitted.com/{state_slug}/#faq",
      "mainEntity": [
        {{"@type": "Question", "name": "How many cities in {state_name} are covered?", "acceptedAnswer": {{"@type": "Answer", "text": "RentPermitted covers {n} cities in {state_name}: {city_names}."}}}},
        {{"@type": "Question", "name": "Does {state_name} have state-wide STR laws?", "acceptedAnswer": {{"@type": "Answer", "text": "{state_name} regulates short-term rentals primarily at the city level. Some states have preemption laws, others leave regulation entirely to municipalities. Check each city's page for specific requirements."}}}},
        {{"@type": "Question", "name": "Which {state_name} city is most STR-friendly?", "acceptedAnswer": {{"@type": "Answer", "text": "This varies. Our risk ranking on this page orders {state_name} cities from most restrictive to most investment-friendly based on fees, caps, and primary residence requirements."}}}}
      ]
    }}
  ]
}}
</script>'''

def gen_state_page(state_name, info):
    """Generate a complete state hub page HTML."""
    abbr = info["abbr"]
    slug = state_slug(state_name)
    cities = info["cities"]
    n = len(cities)

    # Meta
    title = f"{state_name} Short-Term Rental Laws — {n} {'City' if n==1 else 'Cities'} Compared"
    desc = f"Compare STR rules across {n} {state_name} {'city' if n==1 else 'cities'}. License fees, tax rates, and operating rules. Verified May 2026."
    h1 = f"{state_name} ({abbr}) Short-Term Rental Regulations"

    overview = state_overview(state_name, cities)
    table = city_comparison_table(cities)
    ranking = risk_ranking(cities) if n > 1 else ""
    schema = gen_state_schema(state_name, abbr, slug, cities, title, desc)

    # Quick facts
    fee_amounts = []
    for c in cities:
        fa = c.get("fee_amount", "")
        # Extract dollar amount
        import re
        m = re.search(r'\$[\d,]+', fa)
        if m:
            fee_amounts.append(int(m.group().replace('$','').replace(',','')))
    fee_range = f"${min(fee_amounts)}–${max(fee_amounts)}" if len(fee_amounts) >= 2 else (f"${fee_amounts[0]}" if fee_amounts else "Varies")

    archetypes = set(c.get("archetype", "guide") for c in cities)
    if all(a == "warning" for a in archetypes):
        climate = "Restrictive"
    elif all(a == "opportunity" for a in archetypes):
        climate = "Investor-Friendly"
    else:
        climate = "Mixed"

    preemption = "Yes — SB1350" if state_name == "Arizona" else ("Partial — vacation rental preemption" if state_name == "Florida" else "None — city-level regulation")

    quick_facts = f'''<section class="quick-facts">
    <h2>At a Glance</h2>
    <div class="facts-grid">
      <div><span class="fact-label">Cities Covered</span><span class="fact-value">{n} {'city' if n==1 else 'cities'} — {', '.join(c['city'] for c in sorted(cities, key=lambda x: x['city']))}</span></div>
      <div><span class="fact-label">Regulatory Climate</span><span class="fact-value">{climate}</span></div>
      <div><span class="fact-label">License Fee Range</span><span class="fact-value">{fee_range}</span></div>
      <div><span class="fact-label">State Preemption</span><span class="fact-value">{preemption}</span></div>
      <div><span class="fact-label">Primary Residence</span><span class="fact-value">{'Required in some cities' if any('primary residence' in c.get('verdict','').lower() or 'owner-occup' in c.get('verdict','').lower() for c in cities) else 'Not universally required'}</span></div>
      <div><span class="fact-label">Last Verified</span><span class="fact-value"><time datetime="2026-05-15">May 2026</time></span></div>
    </div>
  </section>'''

    # TOC
    toc_sections = [("overview", "Overview"), ("risk-ranking", "Risk Ranking"), ("city-comparison", "City Comparison"), ("faq", "FAQ")]
    toc = '\n  <nav class="toc" aria-label="Table of Contents">\n    <strong>On this page:</strong>\n    ' + '\n    '.join(f'<a href="#{s[0]}">{s[1]}</a>' for s in toc_sections) + '\n  </nav>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="https://www.rentpermitted.com/{slug}/">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://www.rentpermitted.com/{slug}/">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles/global.css">
</head>
<body>
<header>
  <div class="header-inner">
    <a href="/" class="logo">RentPermitted</a>
    <button class="hamburger" aria-label="Menu" aria-expanded="false">
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
    </button>
    <nav id="main-nav">
      <a href="/">Home</a>
      <a href="/#cities">Browse Cities</a>
      <a href="/about/">About</a>
      <a href="/contact/">Contact</a>
    </nav>
  </div>
</header>

<main class="state-page">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">Home</a>
    <span class="breadcrumb-sep">›</span>
    <span>{state_name}</span>
  </nav>

  <h1>{h1}</h1>
  <p class="subtitle">{desc}</p>

  {quick_facts}

  {toc}

  <h2 id="overview">Regulatory Overview</h2>
  <p>{overview}</p>

  {ranking}

  <h2 id="city-comparison">City Comparison — {n} {'City' if n==1 else 'Cities'}</h2>
  <p>All {state_name} cities covered by RentPermitted, ranked and compared:</p>
  {table}

  <h2 id="faq">Frequently Asked Questions</h2>
  <details><summary>How many cities in {state_name} does RentPermitted cover?</summary><p>We cover {n} {'city' if n==1 else 'cities'} in {state_name}: {', '.join(c['city'] for c in sorted(cities, key=lambda x: x['city']))}.</p></details>
  <details><summary>Does {state_name} have state-wide STR laws?</summary><p>{state_name} regulates short-term rentals primarily at the city level. Check each individual city page for specific license requirements, fees, and operating rules.</p></details>
  <details><summary>Which {state_name} city is best for STR investment?</summary><p>This depends on your strategy — owner-occupant vs. pure investor. See our risk ranking above for a city-by-city comparison within {state_name}.</p></details>

  <div class="disclaimer">
    <p><strong>Disclaimer:</strong> Data sourced from official {state_name} city websites and state statutes. Regulations change — verify with local authorities before making investment decisions. Last comprehensive review: May 2026.</p>
    <p>RentPermitted is not a government agency. We compile public information for educational purposes.</p>
  </div>
</main>

<footer>
  <p>RentPermitted — Short-term rental regulations, made clear. Not affiliated with any government agency.</p>
  <p><a href="/affiliate-disclosure/">Affiliate Disclosure</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
</footer>

{schema}
<script>
document.addEventListener("DOMContentLoaded",function(){{var b=document.querySelector(".hamburger");if(!b)return;b.addEventListener("click",function(){{var e=this.getAttribute("aria-expanded")==="true";this.setAttribute("aria-expanded",!e);document.getElementById("main-nav").classList.toggle("active",!e)}})}});
</script>
</body>
</html>'''

# ====== MAIN ======
if __name__ == "__main__":
    for state_name, info in sorted(STATES.items()):
        slug = state_slug(state_name)
        page_dir = os.path.join(BASE, slug)
        os.makedirs(page_dir, exist_ok=True)

        html_content = gen_state_page(state_name, info)
        out_path = os.path.join(page_dir, "index.html")
        with open(out_path, "w") as f:
            f.write(html_content)

        print(f"  ✓ {state_name:20s} → /{slug}/ ({len(info['cities'])} cities, {len(html_content):,} bytes)")

    print(f"\n✅ Generated {len(STATES)} state hub pages")
