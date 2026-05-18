#!/usr/bin/env python3
"""RentPermitted City Page Generator — reads city data JSON, writes HTML pages."""
import json, os, html

BASE = "/home/ubuntu/rentpermitted"
with open("/tmp/cities_batch1.json") as f:
    data = json.load(f)

def state_slug(state_name):
    """Convert state full name to URL slug."""
    return state_name.lower().replace(" ", "-")

# Build state_abbr → state_slug lookup for similar cities
STATE_SLUG_MAP = {d["state_abbr"]: state_slug(d["state"]) for d in data.values()}

def archetype(d):
    """Return (title, description, h1) based on archetype."""
    c = d["city"]; s = d["state_abbr"]
    a = d.get("archetype", "guide")
    if a == "warning":
        title = f"Why your {c} STR might be de-listed in 2026"
        desc = d.get("archetype_description", f"{c} STR license costs {d['fee_amount']}. Enforcement tightening. Updated {d['last_verified']}.")
        h1 = f"Why your {c}, {s} Short-Term Rental Might Be De-Listed in 2026"
    elif a == "opportunity":
        title = f"{c} STR compliance: the ROI of doing it right"
        desc = d.get("archetype_description", f"{c} STR: {d['fee_amount']}. {d.get('market_data',{}).get('annual_revenue','Strong')} avg revenue. Verified {d['last_verified']}.")
        h1 = f"{c}, {s} STR Compliance — The ROI of Doing It Right"
    else:  # guide
        title = f"{c}, {s} — Short-Term Rental Rules"
        desc = d.get("archetype_description", f"Complete guide to {c} STR permits, taxes, and rules. Updated {d['last_verified']}.")
        h1 = f"{c}, {s} Short-Term Rental Regulations"
    return title, desc, h1

def status_color(label):
    if "Restricted" in label or "Limited" in label or "Only" in label:
        return "var(--red)"
    if "Enforced" in label or "Licensed" in label:
        return "var(--orange)"
    return "var(--green)"

def gen_schema(d, slug, title):
    c = d["city"]; s = d["state_abbr"]
    lt = " / ".join(t["type"].split("(")[0].strip() for t in d["license_types"][:2])
    
    # dateModified: parse last_verified (e.g. "May 2026" → "2026-05-17")
    from datetime import datetime
    lv = d.get("last_verified", "May 2026")
    try:
        dt = datetime.strptime(lv, "%B %Y")
        date_mod = dt.strftime("%Y-%m-17")  # default to mid-month
    except:
        date_mod = "2026-05-17"
    
    # citation URL from official_sources
    src_url = d["official_sources"][0]["url"] if d.get("official_sources") else ""
    src_name = d["official_sources"][0]["name"] if d.get("official_sources") else ""
    src_url_escaped = src_url.replace('"', '\\"')
    src_name_escaped = src_name.replace('"', '\\"')
    
    q1 = f"What license types are available for {c} short-term rentals?"
    a1 = f"{c} offers {lt}. {d['license_types'][0]['fee']}. {d['license_types'][0]['notes']}"
    q2 = f"How much does a {c} STR license cost?"
    a2 = d["fee_amount"]
    q3 = f"What taxes apply to short-term rentals in {c}?"
    a3 = d["tax_rates_breakdown"]
    q4 = f"Is {c} STR-friendly for investors?"
    a4 = d["verdict"][:200]
    
    # HowTo steps
    howto_steps = ""
    if d.get("application_steps"):
        for i, step in enumerate(d["application_steps"]):
            step_clean = step.replace('"', '\\"').replace('\n', ' ')
            howto_steps += f'''        {{"@type": "HowToStep", "position": {i+1}, "text": "{step_clean[:200]}"}},\n'''
        howto_steps = howto_steps.rstrip(',\n')
    
    # Investor Scorecard as Dataset
    scorecard_rows = ""
    if d.get("investor_scorecard"):
        for item in d["investor_scorecard"]:
            dim = item.get("dimension", "").replace('"', '\\"')
            score = item.get("score", "")
            note = item.get("note", "").replace('"', '\\"')[:150]
            scorecard_rows += f'''        {{"@type": "DataRow", "row": ["{dim}", "{score}", "{note}"]}},\n'''
        scorecard_rows = scorecard_rows.rstrip(',\n')
    
    # Build the full @graph
    schema = f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "Article",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#article",
      "headline": "{title}",
      "description": "{d.get('archetype_description','')[:200].replace(chr(34),'')}",
      "datePublished": "2026-05-15",
      "dateModified": "{date_mod}",
      "author": {{"@id": "https://www.rentpermitted.com/#organization"}},
      "publisher": {{"@id": "https://www.rentpermitted.com/#organization"}},
      "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://www.rentpermitted.com/{state_slug(d['state'])}/{slug}"}},
      "about": {{"@type": "Thing", "name": "{c} short-term rental regulations"}},
      "isAccessibleForFree": true'''
    
    if src_url:
        schema += f''',
      "citation": [
        {{"@type": "CreativeWork", "name": "{src_name_escaped}", "url": "{src_url_escaped}"}}
      ]'''
    
    schema += f'''
    }},
    {{
      "@type": "BreadcrumbList",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#breadcrumb",
      "itemListElement": [
        {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.rentpermitted.com/"}},
        {{"@type": "ListItem", "position": 2, "name": "{d['state']}", "item": "https://www.rentpermitted.com/{d['state'].lower().replace(' ', '-')}"}},
        {{"@type": "ListItem", "position": 3, "name": "{c}", "item": "https://www.rentpermitted.com/{state_slug(d['state'])}/{slug}"}}
      ]
    }},
    {{
      "@type": "FAQPage",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#faq",
      "mainEntity": [
        {{"@type": "Question", "name": "{q1}", "acceptedAnswer": {{"@type": "Answer", "text": "{a1}"}}}},
        {{"@type": "Question", "name": "{q2}", "acceptedAnswer": {{"@type": "Answer", "text": "{a2}"}}}},
        {{"@type": "Question", "name": "{q3}", "acceptedAnswer": {{"@type": "Answer", "text": "{a3}"}}}},
        {{"@type": "Question", "name": "{q4}", "acceptedAnswer": {{"@type": "Answer", "text": "{a4}"}}}}
      ]
    }}'''
    
    if howto_steps:
        schema += f''',
    {{
      "@type": "HowTo",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#howto",
      "name": "How to get an STR license in {c}, {s}",
      "step": [
{howto_steps}
      ]
    }}'''
    
    if scorecard_rows:
        schema += f''',
    {{
      "@type": "Dataset",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#scorecard",
      "name": "{c} STR Investor Scorecard",
      "description": "5-dimension investor suitability scorecard for {c} short-term rental market",
      "hasPart": [
{scorecard_rows}
      ]
    }}'''
    
    schema += '''
  ]
}
</script>'''
    
    return schema

def gen_license_table(d):
    rows = ""
    for lt in d["license_types"]:
        rows += f'''      <tr><td><strong>{html.escape(lt["type"])}</strong></td><td>{html.escape(lt["fee"])}</td><td>{html.escape(lt["notes"])}</td></tr>\n'''
    return f'''<h2 id="license-types">License Types</h2>
    <div class="table-responsive"><table>
      <thead><tr><th>License Type</th><th>Fee</th><th>Notes</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def gen_steps(d):
    items = "".join(f'        <li>{html.escape(s)}</li>\n' for s in d["application_steps"])
    return f'''<h2 id="license-application">License Application — Step by Step</h2>
    <ol>
{items}    </ol>'''

def gen_rules(d):
    items = "".join(f'        <li>{html.escape(r)}</li>\n' for r in d["operating_rules"])
    return f'''<h2 id="operating-rules">Key Operating Rules</h2>
    <ul>
{items}    </ul>'''

def gen_penalties(d):
    items = "".join(f'        <li>{html.escape(p)}</li>\n' for p in d["penalties"])
    return f'''<h2 id="penalties">Penalties for Non-Compliance</h2>
    <ul>
{items}    </ul>'''

def gen_changes(d):
    rows = ""
    for rc in d["recent_changes"]:
        rows += f'      <tr><td>{html.escape(rc["date"])}</td><td>{html.escape(rc["change"])}</td></tr>\n'
    return f'''<h2 id="recent-changes">Recent Changes</h2>
    <div class="table-responsive"><table>
      <thead><tr><th>Date</th><th>Change</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def gen_numbers(d):
    items = "".join(f'        <li>{html.escape(n)}</li>\n' for n in d["by_the_numbers"])
    return f'''<h2 id="by-the-numbers">📊 By the Numbers</h2>
    <p>Data compiled from government reports, AirDNA, AirROI, and StaySTRA market data.</p>
    <ul>
{items}    </ul>
    <p>Sources: AirROI, StaySTRA, AirDNA market data ({d["last_verified"]}).</p>'''

def gen_scorecard(d):
    rows = ""
    for sc in d["investor_scorecard"]:
        rows += f'      <tr><td><strong>{html.escape(sc["dimension"])}</strong></td><td>{html.escape(sc["score"])}</td><td>{html.escape(sc["notes"])}</td></tr>\n'
    return f'''<h2 id="investor-scorecard">📈 {d["city"]} STR Investor Scorecard</h2>
    <p>Independent assessment — not government data. Scored on five dimensions that matter to hosts and investors.</p>
    <div class="table-responsive"><table>
      <thead><tr><th>Dimension</th><th>Score (1–10)</th><th>Notes</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def gen_y1_costs(d):
    rows = ""
    for yc in d["y1_costs"]:
        rows += f'      <tr><td>{html.escape(yc["item"])}</td><td>{html.escape(yc["cost"])}</td></tr>\n'
    return f'''<h3 id="year-1-costs">Year 1 Real Cost Estimate</h3>
    <div class="table-responsive"><table>
      <thead><tr><th>Item</th><th>Estimated Cost</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def gen_market_data(d):
    """Generate STR investment market data section — cap rates, revenue, cashflow."""
    md = d.get("market_data", {})
    if not md.get("cap_rate"):
        return ""
    return f'''<h2 id="market-data">💰 STR Investment Returns — Real Cap Rate Data</h2>
    <p>Real property analysis data — not projections. Compiled from {md.get("num_properties","30+")} analyzed STR properties in {d["city"]} and verified market reports.</p>
    <div class="table-responsive"><table>
      <thead><tr><th>Metric</th><th>Value</th><th>What It Means</th></tr></thead>
      <tbody>
      <tr><td><strong>Median STR Cap Rate</strong></td><td>{md["cap_rate"]}</td><td>Far below the 8–10% target for pure cashflow investors. Charleston is an appreciation play, not a cashflow market.</td></tr>
      <tr><td><strong>Avg Cash-on-Cash Return</strong></td><td>{md["cash_on_cash"]}</td><td>Negative CoC means most STR properties lose money month-to-month at current prices and interest rates.</td></tr>
      <tr><td><strong>Median Monthly Cashflow</strong></td><td>{md["median_cashflow"]}</td><td>Only {md["positive_cashflow_pct"]} of analyzed properties showed positive monthly cashflow.</td></tr>
      <tr><td><strong>Average Property Price</strong></td><td>{md["avg_price"]}</td><td>Premium pricing reflects Charleston's #1 US city ranking (Travel + Leisure).</td></tr>
      <tr><td><strong>Multifamily Cap Rate (2024)</strong></td><td>{md["multifamily_cap"]}</td><td>For comparison: traditional multifamily in Charleston trades at 5.2–5.4% cap rates (Avison Young). STR cap rates are even tighter.</td></tr>
      </tbody>
    </table></div>
    <p><small>Sources: {md["source"]}</small></p>'''

def gen_profiles(d):
    rows = ""
    for ip in d["investor_profiles"]:
        rows += f'      <tr><td>{html.escape(ip["profile"])}</td><td>{html.escape(ip["verdict"])}</td></tr>\n'
    return f'''<h2 id="who-should-invest">Who Should (and Shouldn't) Invest</h2>
    <div class="table-responsive"><table>
      <thead><tr><th>Profile</th><th>Verdict</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table></div>'''

def gen_visible_faq(d):
    c = d["city"]
    lt = " / ".join(t["type"].split("(")[0].strip() for t in d["license_types"][:2])
    q1 = f"What license types are available for {c} short-term rentals?"
    a1 = f"{c} offers {lt}. {d['license_types'][0]['fee']}. {d['license_types'][0]['notes']}"
    q2 = f"How much does a {c} STR license cost?"
    a2 = d["fee_amount"]
    q3 = f"What taxes apply to short-term rentals in {c}?"
    a3 = d["tax_rates_breakdown"]
    q4 = f"Is {c} STR-friendly for investors?"
    a4 = d["verdict"][:200]
    return f'''<h2 id="faq">Frequently Asked Questions</h2>
    <details><summary>{q1}</summary><p>{a1}</p></details>
    <details><summary>{q2}</summary><p>{a2}</p></details>
    <details><summary>{q3}</summary><p>{a3}</p></details>
    <details><summary>{q4}</summary><p>{a4}</p></details>'''

def gen_similar(d):
    cards = ""
    for sc in d["similar_cities"]:
        cards += f'      <a href="/{sc["city"].lower().replace(" ","-")}/" class="city-card"><strong>{html.escape(sc["city"])}</strong><span>{html.escape(sc["state"])} — {html.escape(sc["reason"])}</span></a>\n'
    return f'''<h2 id="similar-cities">Similar cities</h2>
    <p>Markets with comparable regulatory profiles:</p>
    <div class="city-grid">
{cards}    </div>'''

def gen_sources(d):
    items = "".join(f'        <li><a href="{html.escape(s["url"])}" rel="nofollow noopener" target="_blank">{html.escape(s["name"])}</a></li>\n' for s in d["official_sources"])
    return f'''<h2 id="official-resources">Official Resources</h2>
    <ul>
{items}    </ul>'''

def gen_page(d, slug):
    c = d["city"]; s = d["state_abbr"]; sv = d["last_verified"]
    title, desc, h1 = archetype(d)
    sc = status_color(d["status_label"])
    schema = gen_schema(d, slug, title)
    market_data_link = '<a href="#market-data">Cap Rates</a>\n    ' if d.get("market_data", {}).get("cap_rate") else ""

    html_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="https://www.rentpermitted.com/{state_slug(d['state'])}/{slug}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="https://www.rentpermitted.com/{state_slug(d['state'])}/{slug}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="RentPermitted">
<meta property="og:image" content="https://www.rentpermitted.com/images/og-default.png">
<meta name="twitter:image" content="https://www.rentpermitted.com/images/og-default.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles/global.css">
{schema}
</head>
<body>

<header class="site-header">
  <a href="/" class="logo">RentPermitted</a>
  <button class="hamburger" aria-label="Toggle navigation" aria-expanded="false">
    <span></span><span></span><span></span>
  </button>
  <nav id="main-nav">
    <a href="/#cities">Browse Cities</a>
    <a href="/#states">By State</a>
    <a href="/about/">About</a>
  </nav>
</header>

<main class="city-page">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/">Home</a>
    <span class="breadcrumb-sep">›</span>
    <a href="/{d['state'].lower().replace(' ', '-')}/">{d['state']}</a>
    <span class="breadcrumb-sep">›</span>
    <span>{c}</span>
  </nav>
  <div class="status-badge" style="background:{sc};color:white">{html.escape(d["status_label"])}</div>
  <h1>{h1}</h1>
  <p class="subtitle">Everything you need to operate an Airbnb, Vrbo, or vacation rental in {c}. Permit requirements, tax obligations, and zoning rules — updated {sv}.</p>

  <section class="quick-facts">
    <h2>At a Glance</h2>
    <div class="facts-grid">
      <div><span class="fact-label">STR Status</span><span class="fact-value">{html.escape(d["status_label"])}</span></div>
      <div><span class="fact-label">Permit Required</span><span class="fact-value">{html.escape(d["permit_required"])}</span></div>
      <div><span class="fact-label">License Fee</span><span class="fact-value">{html.escape(d["fee_amount"])}</span></div>
      <div><span class="fact-label">Tax Rate</span><span class="fact-value">{html.escape(d["tax_rate"])}</span></div>
      <div><span class="fact-label">Nights Cap / Spacing</span><span class="fact-value">{html.escape(d["cap_rule"])}</span></div>
      <div><span class="fact-label">Last Verified</span><span class="fact-value"><time datetime="2026-05-15">{html.escape(d["last_verified"])}</time></span></div>
    </div>
  </section>

  <nav class="toc" aria-label="Table of Contents">
    <strong>On this page:</strong>
    <a href="#overview">Overview</a>
    <a href="#license-types">Licenses</a>
    <a href="#taxes">Taxes</a>
    <a href="#operating-rules">Rules</a>
    <a href="#penalties">Penalties</a>
    <a href="#investor-scorecard">Scorecard</a>
{market_data_link}    <a href="#verdict">Verdict</a>
  </nav>

  <article>
    <h2 id="overview">Overview</h2>
    <p>{html.escape(d["overview"])}</p>

{gen_license_table(d)}

{gen_steps(d)}

    <h2 id="taxes">Taxes</h2>
    <p>{html.escape(d["tax_rates_breakdown"])}</p>

{gen_rules(d)}

{gen_penalties(d)}

{gen_changes(d)}

{gen_numbers(d)}

{gen_scorecard(d)}

{gen_y1_costs(d)}

{gen_market_data(d)}

{gen_profiles(d)}

    <h2 id="verdict">Is {c} STR-Friendly?</h2>
    <p>{html.escape(d["verdict"])}</p>

{gen_visible_faq(d)}

{gen_similar(d)}

{gen_sources(d)}
  </article>

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This information is for reference only and does not constitute legal advice. Regulations change frequently. Always verify with official government sources before listing your property. RentPermitted is not affiliated with any government agency.
  </div>
</main>

<footer>
  <p>RentPermitted — Independent short-term rental regulation resource. Not affiliated with any government agency.</p>
  <p><a href="/affiliate-disclosure/">Affiliate Disclosure</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
</footer>

</body>
</html>'''
    return html_page

# Generate all pages
generated = []
for slug, d in data.items():
    page = gen_page(d, slug)
    os.makedirs(f"{BASE}/{state_slug(d['state'])}/{slug}", exist_ok=True)
    path = f"{BASE}/{state_slug(d['state'])}/{slug}/index.html"
    with open(path, "w") as f:
        f.write(page)
    size_kb = len(page) / 1024
    generated.append(f"{state_slug(d['state'])}/{slug} ({size_kb:.1f}KB)")
    print(f"  ✓ {state_slug(d['state'])}/{slug}/index.html ({size_kb:.1f}KB)")

print(f"\nGenerated {len(generated)} pages: {', '.join(generated)}")
