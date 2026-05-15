     1|#!/usr/bin/env python3
     2|"""RentPermitted City Page Generator — reads city data JSON, writes HTML pages."""
     3|import json, os, html
     4|
     5|BASE = "/home/ubuntu/rentpermitted"
     6|with open("/tmp/cities_batch1.json") as f:
     7|    data = json.load(f)
     8|
     9|def archetype(d):
    10|    """Return (title, description, h1) based on archetype."""
    11|    c = d["city"]; s = d["state_abbr"]
    12|    a = d.get("archetype", "guide")
    13|    if a == "warning":
    14|        title = f"Why your {c} STR might be de-listed in 2026"
    15|        desc = d.get("archetype_description", f"{c} STR license costs {d['fee_amount']}. Enforcement tightening. Updated {d['last_verified']}.")
    16|        h1 = f"Why your {c}, {s} Short-Term Rental Might Be De-Listed in 2026"
    17|    elif a == "opportunity":
    18|        title = f"{c} STR compliance: the ROI of doing it right"
    19|        desc = d.get("archetype_description", f"{c} STR: {d['fee_amount']}. {d.get('market_data',{}).get('annual_revenue','Strong')} avg revenue. Verified {d['last_verified']}.")
    20|        h1 = f"{c}, {s} STR Compliance — The ROI of Doing It Right"
    21|    else:  # guide
    22|        title = f"{c}, {s} — Short-Term Rental Rules"
    23|        desc = d.get("archetype_description", f"Complete guide to {c} STR permits, taxes, and rules. Updated {d['last_verified']}.")
    24|        h1 = f"{c}, {s} Short-Term Rental Regulations"
    25|    return title, desc, h1
    26|
    27|def status_color(label):
    28|    if "Restricted" in label or "Limited" in label or "Only" in label:
    29|        return "var(--red)"
    30|    if "Enforced" in label or "Licensed" in label:
    31|        return "var(--orange)"
    32|    return "var(--green)"
    33|
    34|def gen_schema(d, slug, title):
    35|    c = d["city"]; s = d["state_abbr"]
    36|    lt = " / ".join(t["type"].split("(")[0].strip() for t in d["license_types"][:2])
    37|    q1 = f"What license types are available for {c} short-term rentals?"
    38|    a1 = f"{c} offers {lt}. {d['license_types'][0]['fee']}. {d['license_types'][0]['notes']}"
    39|    q2 = f"How much does a {c} STR license cost?"
    40|    a2 = d["fee_amount"]
    41|    q3 = f"What taxes apply to short-term rentals in {c}?"
    42|    a3 = d["tax_rates_breakdown"]
    43|    q4 = f"Is {c} STR-friendly for investors?"
    44|    a4 = d["verdict"][:200]
    45|    return f'''<script type="application/ld+json">
    46|{{
    47|  "@context": "https://schema.org",
    48|  "@graph": [
    49|    {{
    50|      "@type": "Article",
    51|      "@id": "https://www.rentpermitted.com/{slug}/#article",
    52|      "headline": "{title}",
    53|      "description": "{d.get('archetype_description','')[:200].replace(chr(34),'')}",
    54|      "datePublished": "2026-05-15",
    55|      "dateModified": "2026-05-15",
    56|      "author": {"@id": "https://www.rentpermitted.com/#organization"},
    57|      "publisher": {"@id": "https://www.rentpermitted.com/#organization"},
    58|      "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://www.rentpermitted.com/{slug}/"}},
    59|      "about": {{"@type": "Thing", "name": "{c} short-term rental regulations"}},
    60|      "isAccessibleForFree": true
    61|    }},
    62|    {{
    63|      "@type": "BreadcrumbList",
    64|      "@id": "https://www.rentpermitted.com/{slug}/#breadcrumb",
    65|      "itemListElement": [
    66|        {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.rentpermitted.com/"}},
    67|        {{"@type": "ListItem", "position": 2, "name": "{c}, {s}", "item": "https://www.rentpermitted.com/{slug}/"}}
    68|      ]
    69|    }},
    70|    {{
    71|      "@type": "FAQPage",
    72|      "@id": "https://www.rentpermitted.com/{slug}/#faq",
    73|      "mainEntity": [
    74|        {{"@type": "Question", "name": "{q1}", "acceptedAnswer": {{"@type": "Answer", "text": "{a1}"}}}},
    75|        {{"@type": "Question", "name": "{q2}", "acceptedAnswer": {{"@type": "Answer", "text": "{a2}"}}}},
    76|        {{"@type": "Question", "name": "{q3}", "acceptedAnswer": {{"@type": "Answer", "text": "{a3}"}}}},
    77|        {{"@type": "Question", "name": "{q4}", "acceptedAnswer": {{"@type": "Answer", "text": "{a4}"}}}}
    78|      ]
    79|    }}
    80|  ]
    81|}}
    82|</script>'''
    83|
    84|def gen_license_table(d):
    85|    rows = ""
    86|    for lt in d["license_types"]:
    87|        rows += f'''      <tr><td><strong>{html.escape(lt["type"])}</strong></td><td>{html.escape(lt["fee"])}</td><td>{html.escape(lt["notes"])}</td></tr>\n'''
    88|    return f'''<h2>License Types</h2>
    89|    <div class="table-responsive"><table>
    90|      <thead><tr><th>License Type</th><th>Fee</th><th>Notes</th></tr></thead>
    91|      <tbody>
    92|{rows}      </tbody>
    93|    </table></div>'''
    94|
    95|def gen_steps(d):
    96|    items = "".join(f'        <li>{html.escape(s)}</li>\n' for s in d["application_steps"])
    97|    return f'''<h2>License Application — Step by Step</h2>
    98|    <ol>
    99|{items}    </ol>'''
   100|
   101|def gen_rules(d):
   102|    items = "".join(f'        <li>{html.escape(r)}</li>\n' for r in d["operating_rules"])
   103|    return f'''<h2>Key Operating Rules</h2>
   104|    <ul>
   105|{items}    </ul>'''
   106|
   107|def gen_penalties(d):
   108|    items = "".join(f'        <li>{html.escape(p)}</li>\n' for p in d["penalties"])
   109|    return f'''<h2>Penalties for Non-Compliance</h2>
   110|    <ul>
   111|{items}    </ul>'''
   112|
   113|def gen_changes(d):
   114|    rows = ""
   115|    for rc in d["recent_changes"]:
   116|        rows += f'      <tr><td>{html.escape(rc["date"])}</td><td>{html.escape(rc["change"])}</td></tr>\n'
   117|    return f'''<h2>Recent Changes</h2>
   118|    <div class="table-responsive"><table>
   119|      <thead><tr><th>Date</th><th>Change</th></tr></thead>
   120|      <tbody>
   121|{rows}      </tbody>
   122|    </table></div>'''
   123|
   124|def gen_numbers(d):
   125|    items = "".join(f'        <li>{html.escape(n)}</li>\n' for n in d["by_the_numbers"])
   126|    return f'''<h2>📊 By the Numbers</h2>
   127|    <p>Data compiled from government reports, AirDNA, AirROI, and StaySTRA market data.</p>
   128|    <ul>
   129|{items}    </ul>
   130|    <p>Sources: AirROI, StaySTRA, AirDNA market data ({d["last_verified"]}).</p>'''
   131|
   132|def gen_scorecard(d):
   133|    rows = ""
   134|    for sc in d["investor_scorecard"]:
   135|        rows += f'      <tr><td><strong>{html.escape(sc["dimension"])}</strong></td><td>{html.escape(sc["score"])}</td><td>{html.escape(sc["notes"])}</td></tr>\n'
   136|    return f'''<h2>📈 {d["city"]} STR Investor Scorecard</h2>
   137|    <p>Independent assessment — not government data. Scored on five dimensions that matter to hosts and investors.</p>
   138|    <div class="table-responsive"><table>
   139|      <thead><tr><th>Dimension</th><th>Score (1–10)</th><th>Notes</th></tr></thead>
   140|      <tbody>
   141|{rows}      </tbody>
   142|    </table></div>'''
   143|
   144|def gen_y1_costs(d):
   145|    rows = ""
   146|    for yc in d["y1_costs"]:
   147|        rows += f'      <tr><td>{html.escape(yc["item"])}</td><td>{html.escape(yc["cost"])}</td></tr>\n'
   148|    return f'''<h3>Year 1 Real Cost Estimate</h3>
   149|    <div class="table-responsive"><table>
   150|      <thead><tr><th>Item</th><th>Estimated Cost</th></tr></thead>
   151|      <tbody>
   152|{rows}      </tbody>
   153|    </table></div>'''
   154|
   155|def gen_profiles(d):
   156|    rows = ""
   157|    for ip in d["investor_profiles"]:
   158|        rows += f'      <tr><td>{html.escape(ip["profile"])}</td><td>{html.escape(ip["verdict"])}</td></tr>\n'
   159|    return f'''<h2>Who Should (and Shouldn't) Invest</h2>
   160|    <div class="table-responsive"><table>
   161|      <thead><tr><th>Profile</th><th>Verdict</th></tr></thead>
   162|      <tbody>
   163|{rows}      </tbody>
   164|    </table></div>'''
   165|
   166|def gen_similar(d):
   167|    cards = ""
   168|    for sc in d["similar_cities"]:
   169|        cards += f'      <a href="/{sc["city"].lower().replace(" ","-")}/" class="city-card"><strong>{html.escape(sc["city"])}</strong><span>{html.escape(sc["state"])} — {html.escape(sc["reason"])}</span></a>\n'
   170|    return f'''<h2>Similar cities</h2>
   171|    <p>Markets with comparable regulatory profiles:</p>
   172|    <div class="city-grid">
   173|{cards}    </div>'''
   174|
   175|def gen_sources(d):
   176|    items = "".join(f'        <li><a href="{html.escape(s["url"])}" rel="nofollow noopener" target="_blank">{html.escape(s["name"])}</a></li>\n' for s in d["official_sources"])
   177|    return f'''<h2>Official Resources</h2>
   178|    <ul>
   179|{items}    </ul>'''
   180|
   181|def gen_page(d, slug):
   182|    c = d["city"]; s = d["state_abbr"]; sv = d["last_verified"]
   183|    title, desc, h1 = archetype(d)
   184|    sc = status_color(d["status_label"])
   185|    schema = gen_schema(d, slug, title)
   186|
   187|    html_page = f'''<!DOCTYPE html>
   188|<html lang="en">
   189|<head>
   190|<meta charset="UTF-8">
   191|<meta name="viewport" content="width=device-width, initial-scale=1.0">
   192|<title>{title}</title>
   193|<meta name="description" content="{html.escape(desc)}">
   194|<link rel="canonical" href="https://www.rentpermitted.com/{slug}/">
   195|<meta property="og:title" content="{html.escape(title)}">
   196|<meta property="og:description" content="{html.escape(desc)}">
   197|<meta property="og:url" content="https://www.rentpermitted.com/{slug}/">
   198|<meta property="og:type" content="article">
   199|<meta property="og:site_name" content="RentPermitted">
   200|<meta name="twitter:card" content="summary_large_image">
   201|<meta name="twitter:title" content="{html.escape(title)}">
   202|<meta name="twitter:description" content="{html.escape(desc)}">
   203|<link rel="preconnect" href="https://fonts.googleapis.com">
   204|<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   205|<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
   206|<link rel="stylesheet" href="/styles/global.css">
   207|{schema}
   208|</head>
   209|<body>
   210|
   211|<header class="site-header">
   212|  <a href="/" class="logo">RentPermitted</a>
   213|  <nav>
   214|    <a href="/#cities">Browse Cities</a>
   215|    <a href="/#states">By State</a>
   216|    <a href="/about/">About</a>
   217|  </nav>
   218|</header>
   219|
   220|<main class="city-page">
   221|  <div class="status-badge" style="background:{sc};color:white">{html.escape(d["status_label"])}</div>
   222|  <h1>{h1}</h1>
   223|  <p class="subtitle">Everything you need to operate an Airbnb, Vrbo, or vacation rental in {c}. Permit requirements, tax obligations, and zoning rules — updated {sv}.</p>
   224|
   225|  <section class="quick-facts">
   226|    <h2>At a Glance</h2>
   227|    <div class="facts-grid">
   228|      <div><span class="fact-label">STR Status</span><span class="fact-value">{html.escape(d["status_label"])}</span></div>
   229|      <div><span class="fact-label">Permit Required</span><span class="fact-value">{html.escape(d["permit_required"])}</span></div>
   230|      <div><span class="fact-label">License Fee</span><span class="fact-value">{html.escape(d["fee_amount"])}</span></div>
   231|      <div><span class="fact-label">Tax Rate</span><span class="fact-value">{html.escape(d["tax_rate"])}</span></div>
   232|      <div><span class="fact-label">Nights Cap / Spacing</span><span class="fact-value">{html.escape(d["cap_rule"])}</span></div>
   233|      <div><span class="fact-label">Last Verified</span><span class="fact-value">{html.escape(d["last_verified"])}</span></div>
   234|    </div>
   235|  </section>
   236|
   237|  <article>
   238|    <h2>Overview</h2>
   239|    <p>{html.escape(d["overview"])}</p>
   240|
   241|{gen_license_table(d)}
   242|
   243|{gen_steps(d)}
   244|
   245|    <h2>Taxes</h2>
   246|    <p>{html.escape(d["tax_rates_breakdown"])}</p>
   247|
   248|{gen_rules(d)}
   249|
   250|{gen_penalties(d)}
   251|
   252|{gen_changes(d)}
   253|
   254|{gen_numbers(d)}
   255|
   256|{gen_scorecard(d)}
   257|
   258|{gen_y1_costs(d)}
   259|
   260|{gen_profiles(d)}
   261|
   262|    <h2>Is {c} STR-Friendly?</h2>
   263|    <p>{html.escape(d["verdict"])}</p>
   264|
   265|{gen_similar(d)}
   266|
   267|{gen_sources(d)}
   268|  </article>
   269|
   270|  <div class="disclaimer">
   271|    <strong>Disclaimer:</strong> This information is for reference only and does not constitute legal advice. Regulations change frequently. Always verify with official government sources before listing your property. RentPermitted is not affiliated with any government agency.
   272|  </div>
   273|</main>
   274|
   275|<footer>
   276|  <p>RentPermitted — Independent short-term rental regulation resource. Not affiliated with any government agency.</p>
   277|  <p><a href="/affiliate-disclosure/">Affiliate Disclosure</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
   278|</footer>
   279|
   280|</body>
   281|</html>'''
   282|    return html_page
   283|
   284|# Generate all pages
   285|generated = []
   286|for slug, d in data.items():
   287|    page = gen_page(d, slug)
   288|    os.makedirs(f"{BASE}/{slug}", exist_ok=True)
   289|    path = f"{BASE}/{slug}/index.html"
   290|    with open(path, "w") as f:
   291|        f.write(page)
   292|    size_kb = len(page) / 1024
   293|    generated.append(f"{slug} ({size_kb:.1f}KB)")
   294|    print(f"  ✓ {slug}/index.html ({size_kb:.1f}KB)")
   295|
   296|print(f"\nGenerated {len(generated)} pages: {', '.join(generated)}")
   297|