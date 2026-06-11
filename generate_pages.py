#!/usr/bin/env python3
"""RentPermitted City Page Generator: reads city data JSON, writes HTML pages."""
import json, os, html, re

BASE = "/home/ubuntu/rentpermitted"
with open("/tmp/cities_batch1.json") as f:
    data = json.load(f)

def state_slug(state_name):
    """Convert state full name to URL slug."""
    return state_name.lower().replace(" ", "-")

# Build state_abbr → state_slug lookup for similar cities
STATE_SLUG_MAP = {d["state_abbr"]: state_slug(d["state"]) for d in data.values()}
# Slug → city_data lookup for dynamic reason computation
SLUG_TO_KEY = {d["city"].lower().replace(" ", "-"): k for k, d in data.items()}
# Track which contrast dimensions have been used for each target
_SIM_USED = {}  # {target_slug: set(dimension_id)}

def _get_numeric(val_str):
    """Extract the first dollar amount or number from a string."""
    if not isinstance(val_str, str):
        return None
    nums = re.findall(r'\$([\d,]+(?:\.\d+)?)', val_str)
    if nums:
        return float(nums[0].replace(",", ""))
    nums = re.findall(r'(\d+(?:\.\d+)?)', val_str)
    return float(nums[0]) if nums else None

def _extract_tax_pct(tax_str):
    """Extract combined tax percentage from tax string."""
    if not tax_str:
        return None
    # Try combined rate first: "14.75% combined"
    m = re.search(r'([\d.]+)%\s*(?:combined|total)', tax_str)
    if m:
        return float(m.group(1))
    # Try first percentage
    m = re.search(r'([\d.]+)%', tax_str)
    return float(m.group(1)) if m else None

def _status_severity(label):
    """Map status label to numeric severity (higher = stricter)."""
    s = label.lower()
    if "banned" in s: return 10
    if "heavily restricted" in s: return 9
    if "primary residence" in s: return 8
    if "owner-occupied" in s: return 7
    if "homestay" in s: return 6
    if "lottery" in s or "caps" in s: return 5
    if "resort-zone" in s: return 4
    if "zoning" in s: return 3
    if "licensed" in s or "enforced" in s: return 2
    if "certification" in s: return 1
    return 0

def compute_similar_reason(src_data, target_slug):
    """Generate a contrast-based anchor reason for a Similar Cities link.
    
    Picks the dimension with the greatest contrast between source and target,
    avoiding dimensions already used by other sources linking to the same target.
    Returns (reason_string, dimension_id).
    """
    if target_slug not in SLUG_TO_KEY:
        return f"comparable regulatory profile", "generic"
    tgt_key = SLUG_TO_KEY[target_slug]
    tgt_data = data[tgt_key]
    
    src_city = src_data["city"]
    tgt_city = tgt_data["city"]
    tgt_state = tgt_data["state_abbr"]
    
    # Avoid comparing a city to itself
    if src_data["city"] == tgt_data["city"]:
        return f"comparable regulatory profile", "generic"
    
    # Dimension extractors: (id, score_fn, fmt_fn)
    # score_fn returns (contrast_score, reason_if_selected) where higher score = better contrast
    # fmt_fn formats the reason string
    
    dimensions = []
    src_sev = _status_severity(src_data.get("status_label", ""))
    tgt_sev = _status_severity(tgt_data.get("status_label", ""))
    
    # 1. Regulatory stance contrast
    sev_diff = abs(src_sev - tgt_sev)
    if sev_diff >= 3:
        if src_sev > tgt_sev:
            reason = f"more permissive than {src_city}&#x27;s {src_data['status_label'].lower()} model"
        else:
            reason = f"stricter than {src_city}&#x27;s {src_data['status_label'].lower()} approach"
        dimensions.append(("reg_stance", sev_diff * 10, reason))
    elif sev_diff >= 1:
        if src_sev > tgt_sev:
            reason = f"similar but {src_city} is slightly stricter"
        else:
            reason = f"similar regulatory model: {src_city} is the more relaxed of the two"
        dimensions.append(("reg_stance", sev_diff * 8, reason))
    
    # 2. Fee contrast
    src_fee = _get_numeric(src_data.get("fee_amount", ""))
    tgt_fee = _get_numeric(tgt_data.get("fee_amount", ""))
    if src_fee and tgt_fee and src_fee > 0 and tgt_fee > 0:
        ratio = max(src_fee, tgt_fee) / min(src_fee, tgt_fee)
        if ratio >= 2.0:
            if tgt_fee < src_fee:
                reason = f"similar setup but ${int(tgt_fee)} permits vs {src_city}&#x27;s ${int(src_fee)}"
            else:
                reason = f"same STR class but ${int(tgt_fee)} licenses vs {src_city}&#x27;s ${int(src_fee)}"
            dimensions.append(("fee", int(ratio * 10), reason))
        elif ratio >= 1.3:
            reason = f"fee structure comparable: ${int(tgt_fee)} vs ${int(src_fee)} in {src_city}"
            dimensions.append(("fee", int(ratio * 6), reason))
    
    # 3. Tax contrast
    src_tax = _extract_tax_pct(src_data.get("tax_rate", ""))
    tgt_tax = _extract_tax_pct(tgt_data.get("tax_rate", ""))
    if src_tax and tgt_tax:
        tax_diff = abs(src_tax - tgt_tax)
        if tax_diff >= 3:
            if tgt_tax < src_tax:
                reason = f"lower tax burden: {tgt_tax}% combined vs {src_city}&#x27;s {src_tax}%"
            else:
                reason = f"higher STR tax at {tgt_tax}% combined: {src_city} charges {src_tax}%"
            dimensions.append(("tax", int(tax_diff * 10), reason))
        elif tax_diff >= 1:
            if tgt_tax > src_tax:
                reason = f"{tgt_tax}% combined STR tax vs {src_tax}% in {src_city}"
            else:
                reason = f"tax rates close: {tgt_tax}% vs {src_tax}% in {src_city}"
            dimensions.append(("tax", int(tax_diff * 8), reason))
    
    # 4. Market / tourism contrast (ADR)
    src_adr = None; tgt_adr = None
    src_mkt = src_data.get("market_data", {})
    tgt_mkt = tgt_data.get("market_data", {})
    if isinstance(src_mkt, dict):
        adr_str = src_mkt.get("ADR", src_mkt.get("adr", ""))
        src_adr = _get_numeric(str(adr_str)) if adr_str else None
    if isinstance(tgt_mkt, dict):
        adr_str = tgt_mkt.get("ADR", tgt_mkt.get("adr", ""))
        tgt_adr = _get_numeric(str(adr_str)) if adr_str else None
    
    if src_adr and tgt_adr and src_adr > 50 and tgt_adr > 50:
        ratio = max(src_adr, tgt_adr) / min(src_adr, tgt_adr)
        if ratio >= 1.3:
            if tgt_adr > src_adr:
                reason = f"stronger ADR (${int(tgt_adr)} vs ${int(src_adr)}) with similar regulatory profile"
            else:
                reason = f"${int(tgt_adr)} ADR market: {src_city} averages ${int(src_adr)}"
            dimensions.append(("adr", int(ratio * 10), reason))
        elif ratio >= 1.1:
            reason = f"ADR in the same range: ${int(tgt_adr)} vs ${int(src_adr)}"
            dimensions.append(("adr", int(ratio * 6), reason))
    
    # 5. Cap/limit contrast
    src_cap = src_data.get("cap_rule", "").lower()
    tgt_cap = tgt_data.get("cap_rule", "").lower()
    src_has_cap = any(w in src_cap for w in ("cap", "limit", "maximum", "lottery", "no more than"))
    tgt_has_cap = any(w in tgt_cap for w in ("cap", "limit", "maximum", "lottery", "no more than"))
    if src_has_cap != tgt_has_cap:
        if tgt_has_cap:
            reason = f"has permit caps: {src_city} doesn&#x27;t limit the number of permits"
        else:
            reason = f"no permit caps unlike {src_city}&#x27;s limited system"
        dimensions.append(("cap", 15, reason))
    
    # 6. License type contrast
    src_lt = " ".join(t.get("type","").lower() for t in src_data.get("license_types",[])[:2])
    tgt_lt = " ".join(t.get("type","").lower() for t in tgt_data.get("license_types",[])[:2])
    src_tiered = "tier" in src_lt or "class" in src_lt or "owner-occupied" in src_lt or "non-owner" in src_lt
    tgt_tiered = "tier" in tgt_lt or "class" in tgt_lt or "owner-occupied" in tgt_lt or "non-owner" in tgt_lt
    if src_tiered and not tgt_tiered:
        reason = f"simpler single-license system vs {src_city}&#x27;s tiered model"
        dimensions.append(("license", 12, reason))
    elif tgt_tiered and not src_tiered:
        reason = f"tiered license structure: {src_city} uses a single-license approach"
        dimensions.append(("license", 12, reason))
    
    # 7. State-level context
    src_state = src_data.get("state_abbr", "")
    tgt_state = tgt_data.get("state_abbr", "")
    same_state = (src_state == tgt_state)
    src_preempt = "preempt" in src_data.get("status", "").lower() or "state-protected" in src_data.get("status_label", "").lower()
    tgt_preempt = "preempt" in tgt_data.get("status", "").lower() or "state-protected" in tgt_data.get("status_label", "").lower()
    if same_state and src_preempt:
        reason = f"same {src_state} state preemption protection"
        dimensions.append(("state", 10, reason))
    elif same_state and not src_preempt:
        reason = f"another {src_state} market with local-level STR rules"
        dimensions.append(("state", 5, reason))
    elif src_preempt != tgt_preempt:
        if tgt_preempt:
            reason = f"state-level protection keeps regulation predictable"
        else:
            reason = f"local regulation is the key differentiator from {src_city}"
        dimensions.append(("state", 8, reason))
    
    # Sort by score descending, pick highest unused dimension
    dimensions.sort(key=lambda x: x[1], reverse=True)
    
    if target_slug not in _SIM_USED:
        _SIM_USED[target_slug] = set()
    used = _SIM_USED[target_slug]
    
    for dim_id, score, reason in dimensions:
        if dim_id not in used:
            used.add(dim_id)
            return reason, dim_id
    
    # All dimensions exhausted: use best one anyway with a contextual twist
    if dimensions:
        dim_id, _, reason = dimensions[0]
        return reason, dim_id
    
    # Fallback: generic but data-backed
    return f"comparable {src_data.get('status_label','regulatory').lower()} profile in {tgt_state}", "fallback"

def archetype(d):
    """Return (title, description, h1) based on archetype."""
    c = d["city"]; s = d["state_abbr"]
    if c == "Asheville" and s == "NC":
        title = "Asheville Homestay Permit Rules 2026: When STRs Are Allowed"
        desc = d.get("archetype_description", f"{c} STR: homestay-only. $200/yr, owner must be present, 2BR max. Updated {d['last_verified']}.")
        h1 = title
        return title, desc, h1
    a = d.get("archetype", "guide")
    if a == "warning":
        title = f"Why your {c} STR might be de-listed in 2026"
        desc = d.get("archetype_description", f"{c} STR license costs {d['fee_amount']}. Enforcement tightening. Updated {d['last_verified']}.")
        h1 = f"Why your {c}, {s} Short-Term Rental Might Be De-Listed in 2026"
    elif a == "opportunity":
        title = f"{c} STR compliance: the ROI of doing it right"
        desc = d.get("archetype_description", f"{c} STR: {d['fee_amount']}. {d.get('market_data',{}).get('annual_revenue','Strong')} avg revenue. Verified {d['last_verified']}.")
        h1 = f"{c}, {s} STR Compliance: The ROI of Doing It Right"
    else:  # guide
        title = f"{c}, {s}: Short-Term Rental Rules"
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
    scorecard_vars = ""
    if d.get("investor_scorecard"):
        for item in d["investor_scorecard"]:
            dim = item.get("dimension", "").replace('"', '\\"')
            score = item.get("score", "")
            note = item.get("note", "").replace('"', '\\"')[:150]
            scorecard_vars += f'''        {{"@type": "PropertyValue", "name": "{dim}", "value": "{score}", "description": "{note}"}},\n'''
        scorecard_vars = scorecard_vars.rstrip(',\n')
    
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
    
    if scorecard_vars:
        schema += f''',
    {{
      "@type": "Dataset",
      "@id": "https://www.rentpermitted.com/{state_slug(d["state"])}/{slug}#scorecard",
      "name": "{c} STR Investor Scorecard",
      "description": "5-dimension investor suitability scorecard for {c} short-term rental market",
      "creator": {{"@id": "https://www.rentpermitted.com/#organization"}},
      "license": "https://creativecommons.org/licenses/by/4.0/",
      "variableMeasured": [
{scorecard_vars}
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
    return f'''<h2 id="license-application">License Application: Step by Step</h2>
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
    <p>Sources: AirROI, StaySTRA, AirDNA market data ({html.escape(d["last_verified"])}).</p>'''

def gen_scorecard(d):
    rows = ""
    for sc in d["investor_scorecard"]:
        rows += f'      <tr><td><strong>{html.escape(sc["dimension"])}</strong></td><td>{html.escape(sc["score"])}</td><td>{html.escape(sc["notes"])}</td></tr>\n'
    return f'''<h2 id="investor-scorecard">📈 {d["city"]} STR Investor Scorecard</h2>
    <p>Independent assessment: not government data. Scored on five dimensions that matter to hosts and investors.</p>
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
    """Generate STR investment market data section: cap rates, revenue, cashflow."""
    md = d.get("market_data", {})
    if not md.get("cap_rate"):
        return ""
    return f'''<h2 id="market-data">💰 STR Investment Returns: Real Cap Rate Data</h2>
    <p>Real property analysis data: not projections. Compiled from {md.get("num_properties","30+")} analyzed STR properties in {d["city"]} and verified market reports.</p>
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
    lt_esc = html.escape(lt)
    q1 = f"What license types are available for {c} short-term rentals?"
    a1 = f"{c} offers {lt_esc}. {html.escape(d['license_types'][0]['fee'])}. {html.escape(d['license_types'][0]['notes'])}"
    q2 = f"How much does a {c} STR license cost?"
    a2 = html.escape(d["fee_amount"])
    q3 = f"What taxes apply to short-term rentals in {c}?"
    a3 = html.escape(d["tax_rates_breakdown"])
    q4 = f"Is {c} STR-friendly for investors?"
    a4 = html.escape(d["verdict"][:200])
    return f'''<h2 id="faq">Frequently Asked Questions</h2>
    <details><summary>{q1}</summary><p>{a1}</p></details>
    <details><summary>{q2}</summary><p>{a2}</p></details>
    <details><summary>{q3}</summary><p>{a3}</p></details>
    <details><summary>{q4}</summary><p>{a4}</p></details>'''

def gen_similar(d):
    cards = ""
    for sc in d["similar_cities"]:
        target_slug = sc["city"].lower().replace(" ", "-")
        # v2: use state-hub path (state_slug/city_slug) instead of flat city path
        target_state_slug = STATE_SLUG_MAP.get(sc["state"], "")
        target_path = f"{target_state_slug}/{target_slug}" if target_state_slug else target_slug
        reason, _ = compute_similar_reason(d, target_slug)
        cards += f'      <a href="/{target_path}/" class="city-card"><strong>{html.escape(sc["city"])}</strong><span>{html.escape(sc["state"])}: {reason}</span></a>\n'
    return f'''<h2 id="similar-cities">Similar cities</h2>
    <p>Markets with comparable regulatory profiles:</p>
    <div class="city-grid">
{cards}    </div>'''

# ── GEO Quotable Units: AI extractable blocks ──

def gen_digest(d):
    """Regulation digest: 3-5 sentence summary AI can quote directly.
    Answers the core question: 'Can I STR in [city] and what does it take?'"""
    c = d["city"]; s = d["state_abbr"]
    status = d["status_label"].lower()
    fee = d["fee_amount"]
    tax = d["tax_rate"]
    cap = d["cap_rule"]
    permit = d["permit_required"].lower()

    # Determine regulatory stance: comprehensive matching
    if "banned" in status or "heavily restricted" in status:
        stance = f"Short-term rentals under 30 days are effectively banned in {c}. Enforcement is active and penalties are severe."
    elif "primary residence" in status or "owner-occupied" in status:
        stance = f"{c} requires the host to live on-site. Non-owner-occupied STRs are prohibited or face major barriers."
    elif "homestay" in status and "only" in status:
        stance = f"{c} only allows homestay-style rentals where the host is present during the guest's stay."
    elif "resort-zone" in status or "resort zone" in status:
        stance = f"{c} limits short-term rentals to designated resort zones. Operating outside these areas is prohibited."
    elif "lottery" in status or "caps" in status or "cap" in status.split("-"):
        stance = f"{c} operates a limited permit system. Not everyone who applies gets approved: caps are hard and enforced."
    elif "zoning" in status:
        stance = f"{c} ties STR permits to zoning districts. The wrong address means an automatic denial."
    elif "licensed" in status or "enforced" in status:
        stance = f"{c} requires all short-term rental operators to hold a license. Enforcement is active and non-compliance carries real penalties."
    elif "certification" in status:
        stance = f"{c} requires certification for all STR operators. Operating without one triggers enforcement action."
    elif "registration" in status or "permitted" in status:
        stance = f"{c} allows short-term rentals with registration. The process is straightforward compared to more restrictive cities."
    elif "state-protected" in status:
        stance = f"{c} benefits from Arizona's state law that prevents cities from banning short-term rentals. Local rules still apply but the baseline is favorable."
    else:
        stance = f"{c} regulates short-term rentals through a permit and tax system. Compliance is required before listing any property."

    # Fee sentence: truncate long strings for digest readability
    fee_esc = html.escape(fee)
    if fee.lower() in ("$0", "free", "none", "n/a", "no fee"):
        fee_s = "Registration carries no direct license fee."
    elif "free" in fee.lower().split("+")[-1].strip() and "$" not in fee.lower().split("+")[0]:
        fee_s = "Registration carries no direct license fee."
    elif len(fee) > 60:
        amounts = re.findall(r'\$[\d,]+(?:\.\d+)?(?:\/\w+)?', fee)
        if amounts:
            fee_s = f"The license fee starts at {amounts[0]}."
        else:
            fee_s = f"License fees apply. See details below."
    elif "per unit" in fee.lower() or "per bedroom" in fee.lower():
        fee_s = f"Licensing costs {fee_esc}."
    else:
        fee_s = f"The license costs {fee_esc}."

    # Tax sentence
    tax_s = f"A combined occupancy tax of {html.escape(tax)} applies to all bookings under 30 nights." if tax and tax != "N/A" else ""

    # Cap sentence
    cap_lower = cap.lower() if cap else ""
    if not cap or cap_lower in ("none", "n/a"):
        cap_s = "No night limit applies."
    elif "no night limit" in cap_lower or "no annual night" in cap_lower or "no cap" in cap_lower:
        cap_s = "No night limit applies: but zoning and density restrictions may still apply."
    elif "unlimited" in cap_lower:
        cap_s = "No night limit applies."
    elif len(cap) > 50:
        # Long cap description: summarize
        cap_s = "Night limits and zoning restrictions apply. See details below."
    else:
        cap_s = f"Nights are capped at {cap}."

    sentences = [stance, fee_s]
    if tax_s:
        sentences.append(tax_s)
    sentences.append(cap_s)

    return f'''<section class="digest">
    <h2>Regulation Digest</h2>
    <blockquote>
      <p>{" ".join(sentences)}</p>
    </blockquote>
  </section>'''


def gen_key_stats(d):
    """Key numbers in quotable paragraph: what AI cites for comparisons."""
    c = d["city"]; s = d["state_abbr"]
    fee = d["fee_amount"]
    tax = d["tax_rate"]
    cap = d["cap_rule"]

    stats = []
    stats.append(f"{c}, {s} charges {html.escape(fee)} for an STR license.")
    if tax and tax != "N/A":
        stats.append(f"The total occupancy tax rate is {html.escape(tax)}.")
    cap_lower = cap.lower() if cap else ""
    if cap and cap_lower not in ("none", "n/a") and "no night limit" not in cap_lower and "no cap" not in cap_lower and "unlimited" not in cap_lower:
        if len(cap) < 50:
            stats.append(f"Nights are capped at {cap}.")
        else:
            stats.append("Night limits and zoning restrictions apply.")

    # Add market data if available
    md = d.get("market_data", {})
    if md.get("adr") and md.get("annual_revenue"):
        stats.append(f"Market data shows an average daily rate of {md['adr']} with annual revenue around {md['annual_revenue']}.")

    return f'''<section class="key-stats">
    <h2>Key Numbers</h2>
    <p>{" ".join(stats)}</p>
    <p class="meta">Data verified {html.escape(d["last_verified"])}. Always confirm with official sources before acting.</p>
  </section>'''


def gen_enforcement(d):
    """Enforcement reality: cold, fragment-style. No sugar-coating."""
    c = d["city"]
    penalties = d.get("penalties", [])
    if not penalties:
        return ""

    # Extract enforcement signals
    penalty_texts = [p.lower() for p in penalties]
    has_fines = any("fine" in p or "penalty" in p or "$" in p for p in penalty_texts)
    has_criminal = any("misdemeanor" in p or "criminal" in p or "jail" in p for p in penalty_texts)
    has_platform = any("platform" in p or "delist" in p or "airbnb" in p.lower() for p in penalty_texts)
    has_enforcement = any("enforcement" in p or "violation" in p or "subject to" in p for p in penalty_texts)

    parts = []
    if has_fines:
        parts.append("Fines are real.")
    if has_criminal:
        parts.append("Criminal penalties are possible for repeat violations.")
    if has_platform:
        parts.append("Platforms cooperate with enforcement: listings get de-listed.")
    if has_enforcement and not parts:
        parts.append("Enforcement is active: violations trigger penalties.")

    if not parts:
        return ""

    return f'''<section class="enforcement-note">
    <h2>Enforcement Reality</h2>
    <p class="cold">{" ".join(parts)}</p>
  </section>'''


def gen_bottom_line(d):
    """Single-sentence bottom line: what AI cites as final judgment."""
    c = d["city"]
    verdict = d.get("verdict", "")
    archetype = d.get("archetype", "guide")

    # Extract a clean one-liner from verdict
    if verdict:
        # Take first sentence
        first = verdict.split(".")[0].strip()
        if len(first) > 30:
            return f'''<section class="bottom-line">
    <p><strong>Bottom line:</strong> {html.escape(first)}.</p>
  </section>'''

    # Fallback
    if archetype == "warning":
        return f'''<section class="bottom-line">
    <p><strong>Bottom line:</strong> {c} is a high-risk STR market. Compliance is not optional.</p>
  </section>'''
    elif archetype == "opportunity":
        return f'''<section class="bottom-line">
    <p><strong>Bottom line:</strong> {c} offers strong returns for compliant operators who do the paperwork.</p>
  </section>'''
    else:
        return f'''<section class="bottom-line">
    <p><strong>Bottom line:</strong> STR operation in {c} requires a license. Follow the steps or risk enforcement.</p>
  </section>'''


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
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-MSME4WL2XB"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-MSME4WL2XB');
</script>
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
  <p class="subtitle">Everything you need to operate an Airbnb, Vrbo, or vacation rental in {c}. Permit requirements, tax obligations, and zoning rules: updated {html.escape(sv)}.</p>

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

{gen_digest(d)}

{gen_key_stats(d)}

{gen_license_table(d)}

{gen_steps(d)}

    <h2 id="taxes">Taxes</h2>
    <p>{html.escape(d["tax_rates_breakdown"])}</p>

{gen_rules(d)}

{gen_penalties(d)}

{gen_enforcement(d)}

{gen_changes(d)}

{gen_numbers(d)}

{gen_scorecard(d)}

{gen_y1_costs(d)}

{gen_market_data(d)}

{gen_profiles(d)}

    <h2 id="verdict">Is {c} STR-Friendly?</h2>
    <p>{html.escape(d["verdict"])}</p>

{gen_bottom_line(d)}

{gen_visible_faq(d)}

{gen_similar(d)}

{gen_sources(d)}
  </article>

  <div class="disclaimer">
    <strong>Disclaimer:</strong> This information is for reference only and does not constitute legal advice. Regulations change frequently. Always verify with official government sources before listing your property. RentPermitted is not affiliated with any government agency.
  </div>
</main>

<footer>
  <p>RentPermitted: Independent short-term rental regulation resource. Not affiliated with any government agency.</p>
  <p><a href="/affiliate-disclosure/">Affiliate Disclosure</a> · <a href="/privacy/">Privacy Policy</a> · <a href="/contact/">Contact</a></p>
</footer>

</body>
</html>'''
    return html_page

# Generate all pages
_SIM_USED.clear()
generated = []
for slug, d in data.items():
    page = gen_page(d, slug).replace("—", ":")
    os.makedirs(f"{BASE}/{state_slug(d['state'])}/{slug}", exist_ok=True)
    path = f"{BASE}/{state_slug(d['state'])}/{slug}/index.html"
    with open(path, "w") as f:
        f.write(page)
    size_kb = len(page) / 1024
    generated.append(f"{state_slug(d['state'])}/{slug} ({size_kb:.1f}KB)")
    print(f"  ✓ {state_slug(d['state'])}/{slug}/index.html ({size_kb:.1f}KB)")

print(f"\nGenerated {len(generated)} pages: {', '.join(generated)}")
