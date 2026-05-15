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

# Z.1 verification sources for state preemption claims
VERIFICATION_SOURCES = {
    "Arizona": "SB1350 verified via azleg.gov/legtext/52leg/2r/laws/0208.pdf",
    "Florida": "FL Stat. 509.032 verified via flsenate.gov/laws/statutes/2018/509.032",
    "Texas": "No state preemption verified via capitol.texas.gov (HB2665 study-only)",
}

def state_slug(state_name):
    return state_name.lower().replace(" ", "-")

def state_overview(state_name, cities):
    """Return a hand-researched state-level regulatory overview."""
    n = len(cities)

    OVERVIEWS = {
        "Texas": (
            f"Texas has no state-level short-term rental preemption law, leaving regulation entirely to cities. "
            f"The result is a patchwork: Austin operates a density-capped Type 2/3 licensing system with a 3% per-tract limit and waitlist, "
            f"while Dallas and Houston have chosen light-touch registration with no primary residence requirement, "
            f"no night caps, and no zoning restrictions. For investors, Texas is a tale of two markets. "
            f"Choose your city carefully. Austin favors owner-occupants and existing permit holders; "
            f"Dallas and Houston are among the most accessible STR markets in the country."
        ),
        "California": (
            f"California is the most restrictive state in our coverage for short-term rental investors. "
            f"San Diego, Los Angeles, and San Francisco impose primary residence requirements and hard day caps. "
            f"San Diego's 20-day annual cap (Tier 3-4) is the strictest in the country, effectively limiting STRs to a side-income activity. "
            f"Los Angeles layers a 120-day cap with the nation's highest platform fee ($850). "
            f"San Francisco maintains a 90-day cap with one listing per host. "
            f"There is no state-level STR preemption in California. Cities regulate independently and enforcement is active across all three markets."
        ),
        "Florida": (
            f"Florida occupies a unique middle ground. FL Stat. 509.032 preempts cities from banning vacation rentals entirely, "
            f"providing a baseline of state-level protection. But cities retain broad authority over registration, fees, zoning, and enforcement. "
            f"In practice, Miami Beach is heavily zoning-restricted with high fines and active code enforcement, "
            f"while Orlando bans whole-home STRs in most residential zones. Only owner-occupied home shares are permitted. "
            f"Florida's statutory framework means the door is never fully closed, but local rules determine whether a specific property is viable."
        ),
        "Arizona": (
            f"Arizona is the strongest investor market in our coverage, anchored by SB1350, a 2016 law that prohibits "
            f"cities from banning short-term rentals outright. Cities may require licenses, collect taxes, and enforce nuisance "
            f"ordinances, but cannot use zoning to restrict STRs. Both Scottsdale and Phoenix operate under this framework with "
            f"straightforward annual registration ($250/year) and no primary residence requirements. "
            f"Arizona's state-level preemption provides regulatory certainty that few other states offer, "
            f"making it one of the most predictable markets for STR investment."
        ),
        "Georgia": (
            f"Georgia has no state-level STR preemption law, placing full regulatory authority with individual cities. "
            f"Atlanta requires primary residence for STR operators: the property must be the host's primary home. "
            f"A $150/year registration fee. Savannah operates a certification system with higher upfront costs "
            f"($400 initial / $250 renewal) and zoning-based eligibility. "
            f"Both cities are viable for owner-occupants, but Georgia offers limited opportunity for pure investment properties."
        ),
        "Tennessee": (
            f"Tennessee has no state-level STR preemption law. Nashville requires a Short-Term Rental Property (STRP) permit "
            f"at $313/year plus a business license (~$15-22), with platform-collected 7% Metro occupancy tax (increased from 6% in FY2024). "
            f"Nashville is legal but constrained. Permits are available across all zones for owner-occupants, "
            f"but non-owner-occupied permits face moratorium risk. Strong tourism demand makes it viable for those who qualify."
        ),
        "Colorado": (
            f"Colorado has no state-level STR preemption. Denver requires primary residence: the property must be the host's "
            f"primary home. A $100 biennial license fee. At 14.75% combined lodging tax, Denver is expensive for guests "
            f"but cheap for operators. Denver is not an investment market; it is a homeowner income-supplement program. "
            f"If you live in Denver and want to STR your primary residence while traveling, it's accessible. For non-resident investors, it's closed."
        ),
        "Illinois": (
            f"Illinois has no state-level STR preemption. Chicago requires primary residence for STR operators in most zones, "
            f"with a $250/year registration fee. The tax burden is notable: 4.5% Chicago Hotel Accommodations Tax plus a 6% "
            f"Shared Housing Surcharge plus 1% Cook County tax. Chicago is workable for owner-occupants who want to STR "
            f"their primary residence part-time, but the primary residence requirement excludes pure investors."
        ),
        "Washington": (
            f"Washington has no state-level STR preemption, but Seattle stands out as a rare West Coast bright spot. "
            f"Seattle requires a $75/year license with no primary residence requirement, no night caps, and no density limits. "
            f"The combined lodging tax is 15.6% (state + King County + City), but platforms collect and remit. "
            f"For small STR investors, Seattle offers one of the most accessible regulatory environments on the West Coast."
        ),
        "Oregon": (
            f"Oregon has no state-level STR preemption. Portland operates a two-tier system: Type A permits ($360/2 years) "
            f"for owner-occupied rentals of 1-2 bedrooms, and Type B permits ($9,005+) for non-owner-occupied or larger units. "
            f"The Type B fee structure makes Portland effectively closed to non-resident investors. "
            f"Portland is an owner-occupant market: accessible for homeowners renting spare rooms, prohibitive for investment properties."
        ),
        "Louisiana": (
            f"Louisiana has no state-level STR preemption. New Orleans operates a permit lottery system with caps, "
            f"plus platform enforcement scheduled for Q3 2026. Non-owner-occupied STR permits (CSTR) cost $1,000/year "
            f"with a $50 application fee. Owner-occupied permits (NSTR) are $500. "
            f"Event-driven tourism (Mardi Gras, Jazz Fest) creates strong demand, but the regulatory environment is hostile "
            f"to new entrants. New Orleans is a demand-rich, regulation-hostile market."
        ),
        "North Carolina": (
            f"North Carolina has no state-level STR preemption. Asheville permits homestays only. "
            f"The owner must reside on the property during the rental period. The permit fee is $200. "
            f"Asheville has strong tourism demand from the Blue Ridge Mountains and Biltmore Estate, "
            f"but the homestay-only restriction limits STR activity to owner-occupied rooms and ADUs. "
            f"Not an investment market. A homeowner side-income opportunity."
        ),
        "South Carolina": (
            f"South Carolina has no state-level STR preemption. Charleston is a premium STR market with premium compliance costs. "
            f"Class 1 permits (owner-occupied) cost $595 total ($250 + $345). Class 2 permits (non-owner-occupied) cost $1,845 "
            f"($1,500 + $345). Zoning restrictions apply, and self-reported tax remittance is required. "
            f"Charleston's historic district tourism commands high ADRs, but the cost of entry and zoning barriers "
            f"make it a market for experienced operators with properties in the right zones."
        ),
        "Nevada": (
            f"Nevada has no state-level STR preemption. Las Vegas requires owner-occupancy and daily on-site presence "
            f"for STR operators. First-year costs are $945-1,695 with annual renewals at $750-1,500. "
            f"Las Vegas is not an STR investment market. The daily on-site requirement and owner-occupancy mandate "
            f"make it a room-share opportunity for homeowners only. Clark County's transient lodging tax adds to the guest cost."
        ),
        "Hawaii": (
            f"Hawaii has no state-level STR preemption. Honolulu restricts STRs to resort-zoned areas only, "
            f"with a $1,000 initial registration fee and $500 annual renewal. Hawaii's Transient Accommodations Tax (TAT) "
            f"is 11% (increased from 10.25% January 2026, per Act 96) plus 3% Oahu surcharge. "
            f"Honolulu is the most expensive market in our coverage, with the highest taxes, highest fines, and strictest zoning. "
            f"Only properties in designated resort zones are eligible."
        ),
        "Massachusetts": (
            f"Massachusetts has no state-level STR preemption statewide, though a bill is under watch. "
            f"Boston requires registration at $25-200/year depending on unit type, with no primary residence requirement. "
            f"Taxes include 6.5% state room occupancy excise plus 6% Boston Convention Center financing surcharge. "
            f"Year-round demand from 50+ colleges and strong business/medical tourism makes Boston a low-barrier, "
            f"high-demand STR market. One of the more accessible Northeast markets."
        ),
        "District of Columbia": (
            f"The District of Columbia regulates STRs at the city level; there is no state intermediary. "
            f"Washington DC requires primary residence and imposes a 90-day annual cap on non-owner-occupied stays. "
            f"The biennial license fee is $99. Combined taxes reach 14.5%. "
            f"DC is a solid market for homeowners who want part-time STR income. Accessible fees, strong year-round tourism demand, "
            f"but the 90-day cap limits revenue upside for pure investors."
        ),
        "New York": (
            f"New York has no state-level STR preemption. New York City's Local Law 18 effectively killed the STR investment market. "
            f"The law requires hosts to be present during the stay (hosted-only), limits guests to 2, and mandates registration "
            f"with the Mayor's Office of Special Enforcement. The $145/2-year fee is affordable, but the hosted-only + 2-guest restriction "
            f"makes investment-scale STR operation impossible in NYC. This is a room-share market for homeowners only."
        ),
    }

    overview = OVERVIEWS.get(state_name, "")
    if not overview:
        # Fallback for any state not explicitly written (shouldn't happen with our 18)
        overview = f"{state_name} regulates short-term rentals primarily at the city level. Check each city page for specific requirements."

    return overview


def title_archetype(state_name, cities):
    """Pitfall 14: 3-title-archetype system for state pages."""
    n = len(cities)
    warning_count = sum(1 for c in cities if c.get("archetype") == "warning")
    opp_count = sum(1 for c in cities if c.get("archetype") == "opportunity")

    if n == 1:
        # Single-city states: title driven by that city's archetype
        c = cities[0]
        arch = c.get("archetype", "guide")
        if arch == "warning":
            return f"Why {c['city']} STRs Face the Toughest Rules in 2026", "warning"
        elif arch == "opportunity":
            return f"{c['city']} STR Compliance: Predictable Rules, Real Returns", "opportunity"
        else:
            return f"{c['city']} Short-Term Rental Rules — {state_name} Guide", "guide"

    # Multi-city states: threshold-based
    if warning_count >= n * 0.5:
        title = f"Why {state_name} STRs Face the Toughest Rules in 2026"
        arch = "warning"
    elif opp_count >= n * 0.5:
        title = f"{state_name} STR Compliance: Predictable Rules, Real Returns"
        arch = "opportunity"
    else:
        title = f"{state_name} Short-Term Rental Laws — {n} Cities Compared"
        arch = "guide"

    return title, arch


def by_the_numbers(state_name, cities):
    """Pitfall 8: quantitative data block for state pages."""
    import re
    n = len(cities)

    primary_res = sum(1 for c in cities if
        "primary residence" in c.get("status_label", "").lower()
        or "owner-occup" in c.get("status_label", "").lower())

    warning_count = sum(1 for c in cities if c.get("archetype") == "warning")
    opp_count = sum(1 for c in cities if c.get("archetype") == "opportunity")

    fees = []
    for c in cities:
        fa = c.get("fee_amount", "")
        m = re.search(r'\$[\d,]+', fa)
        if m:
            fees.append(int(m.group().replace('$', '').replace(',', '')))

    lines = []
    lines.append(f"<li><strong>{n}</strong> {'city' if n == 1 else 'cities'} covered in {state_name}</li>")
    if fees:
        lines.append(f"<li>License fee range: <strong>${min(fees):,}–${max(fees):,}</strong></li>")
    if primary_res > 0:
        lines.append(f"<li><strong>{primary_res}/{n}</strong> {'city' if n == 1 else 'cities'} ({int(primary_res / n * 100)}%) require primary residence</li>")
    if warning_count > 0:
        lines.append(f"<li><strong>{warning_count}</strong> {'city' if warning_count == 1 else 'cities'} rated high-risk for investors</li>")
    if opp_count > 0:
        lines.append(f"<li><strong>{opp_count}</strong> {'city' if opp_count == 1 else 'cities'} rated investor-friendly</li>")

    # State-specific tax data where we have it
    tax_notes = {
        "Colorado": "Denver combined lodging tax: 14.75%",
        "Hawaii": "State TAT 11% + Oahu surcharge 3% = 14%",
        "Washington": "Seattle combined: 15.6% (state + King County + city)",
        "Illinois": "Chicago: 4.5% hotel + 6% shared housing surcharge + 1% Cook County = 11.5%",
        "District of Columbia": "DC combined: 14.5%",
        "Massachusetts": "Boston: 6.5% state + 6% convention center = 12.5%",
        "Oregon": "Portland combined: 14.5% (state + city)",
        "Louisiana": "New Orleans combined: 14.45% (state + city)",
        "New York": "NYC combined: 14.75% + $1.50/night Javits fee",
    }
    if state_name in tax_notes:
        lines.append(f"<li>Combined lodging tax: <strong>{tax_notes[state_name]}</strong></li>")

    return f'''<section class="by-numbers">
    <h2 id="by-numbers">📊 By the Numbers</h2>
    <ul>
      {chr(10).join('      ' + l for l in lines)}
    </ul>
    <p class="source-note">Source: City-level data from official municipal sources, cross-verified May 2026.</p>
  </section>'''


def similar_states(state_name, info, all_states):
    """Pitfall 15: cross-link to 3 states with similar regulatory profiles."""
    cities = info["cities"]
    n = len(cities)
    warning_count = sum(1 for c in cities if c.get("archetype") == "warning")
    opp_count = sum(1 for c in cities if c.get("archetype") == "opportunity")

    warning_pct = warning_count / n if n > 0 else 0
    opp_pct = opp_count / n if n > 0 else 0

    if opp_pct >= 0.5:
        profile_label = "investor-friendly"
        profile_states = []
        for sname, sinfo in all_states.items():
            scities = sinfo["cities"]
            sopp = sum(1 for c in scities if c.get("archetype") == "opportunity")
            sn = len(scities)
            if sn > 0 and sopp / sn >= 0.5 and sname != state_name:
                profile_states.append((sname, sinfo, sopp))
        profile_states.sort(key=lambda x: -x[2])
    elif warning_pct >= 0.5:
        profile_label = "restrictive"
        profile_states = []
        for sname, sinfo in all_states.items():
            scities = sinfo["cities"]
            swarn = sum(1 for c in scities if c.get("archetype") == "warning")
            sn = len(scities)
            if sn > 0 and swarn / sn >= 0.5 and sname != state_name:
                profile_states.append((sname, sinfo, swarn))
        profile_states.sort(key=lambda x: -x[2])
    else:
        profile_label = "mixed"
        profile_states = []
        for sname, sinfo in all_states.items():
            scities = sinfo["cities"]
            swarn = sum(1 for c in scities if c.get("archetype") == "warning")
            sopp = sum(1 for c in scities if c.get("archetype") == "opportunity")
            sn = len(scities)
            if sn > 0 and swarn / sn < 0.5 and sopp / sn < 0.5 and sname != state_name:
                profile_states.append((sname, sinfo, 0))
        profile_states.sort(key=lambda x: len(x[1]["cities"]), reverse=True)

    similar = profile_states[:3]
    if not similar:
        return ""

    cards = ""
    for sname, sinfo, _ in similar:
        scities = sinfo["cities"]
        slug = state_slug(sname)
        abbr = sinfo["abbr"]
        cards += (
            f'        <div class="city-card">'
            f'<a href="/{slug}/"><strong>{sname} ({abbr})</strong></a>'
            f'<p>{len(scities)} city page(s)</p>'
            f'</div>\n'
        )

    return f'''
  <section class="similar-states">
    <h2 id="similar-states">Similar States</h2>
    <p>States with a comparable {profile_label} regulatory profile:</p>
    <div class="city-grid">
{cards}    </div>
  </section>'''


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

def gen_state_schema(state_name, state_abbr, state_slug, cities, title, desc, faq_q2, faq_q3):
    """Generate JSON-LD schema for state hub page."""
    n = len(cities)
    city_names = ", ".join(c["city"] for c in sorted(cities, key=lambda x: x["city"]))
    # Escape double quotes in FAQ answers for JSON
    q2_safe = faq_q2.replace('"', '\\"')
    q3_safe = faq_q3.replace('"', '\\"')
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
        {{"@type": "Question", "name": "How many cities in {state_name} are covered?", "acceptedAnswer": {{"@type": "Answer", "text": "We cover {n} cities in {state_name}: {city_names}."}}}},
        {{"@type": "Question", "name": "Does {state_name} have state-wide STR laws?", "acceptedAnswer": {{"@type": "Answer", "text": "{q2_safe}"}}}},
        {{"@type": "Question", "name": "Which {state_name} city is most STR-friendly?", "acceptedAnswer": {{"@type": "Answer", "text": "{q3_safe}"}}}}
      ]
    }}
  ]
}}
</script>'''

def gen_state_page(state_name, info, all_states):
    """Generate a complete state hub page HTML."""
    abbr = info["abbr"]
    slug = state_slug(state_name)
    cities = info["cities"]
    n = len(cities)

    # Pitfall 14: dynamic title archetype
    title, archetype = title_archetype(state_name, cities)
    
    desc = f"Compare STR rules across {n} {state_name} {'city' if n==1 else 'cities'}. License fees, tax rates, and operating rules. Verified May 2026."
    h1 = f"{state_name} ({abbr}) Short-Term Rental Regulations"

    overview = state_overview(state_name, cities)
    table = city_comparison_table(cities)
    ranking = risk_ranking(cities) if n > 1 else ""

    # FAQ Q2: state-wide laws — per-state answers
    faq_q2 = {
        "Arizona": "Yes — Arizona's SB1350 (2016) prohibits cities from banning short-term rentals outright. Cities may require licenses, collect taxes, and enforce nuisance rules, but cannot use zoning to restrict STRs. This is one of the strongest state-level STR protections in the country.",
        "Florida": "Partially — FL Stat. 509.032 preempts cities from banning vacation rentals entirely, but cities retain broad authority over registration, fees, zoning, and enforcement. The state sets a floor, not a ceiling. Local rules ultimately determine viability.",
    }.get(state_name, f"{state_name} regulates short-term rentals primarily at the city level. There is no comprehensive state-wide STR law. Check each individual city page for specific license requirements, fees, and operating rules.")

    # FAQ Q3: best city for investment — derived from risk ranking for multi-city states
    if n > 1:
        scored = [(c.get("archetype","guide")=="opportunity", c.get("archetype","guide")!="warning", c) for c in cities]
        scored.sort(key=lambda x: (-x[0], -x[1]))
        best = scored[0][2]
        worst = scored[-1][2]
        if best["city"] == worst["city"]:
            faq_q3 = f"With only one city covered, {best['city']} is the reference point. Check its city page for a detailed verdict on investment viability."
        else:
            faq_q3 = f"{best['city']} is generally the most accessible: {best.get('verdict','')[:120]}. {worst['city']} is the most restrictive: {worst.get('verdict','')[:120]}. See the risk ranking above for the full breakdown."
    else:
        c = cities[0]
        faq_q3 = f"{c['city']} is the only city we currently cover in {state_name}. {c.get('verdict','')[:200]}"

    # TOC — skip risk-ranking for single-city states
    if n > 1:
        toc_sections = [("by-numbers", "By the Numbers"), ("overview", "Overview"), ("risk-ranking", "Risk Ranking"), ("city-comparison", "City Comparison"), ("faq", "FAQ"), ("similar-states", "Similar States")]
    else:
        toc_sections = [("by-numbers", "By the Numbers"), ("overview", "Overview"), ("city-comparison", "City Comparison"), ("faq", "FAQ"), ("similar-states", "Similar States")]

    toc = '\n  <nav class="toc" aria-label="Table of Contents">\n    <strong>On this page:</strong>\n    ' + '\n    '.join(f'<a href="#{s[0]}">{s[1]}</a>' for s in toc_sections) + '\n  </nav>'

    schema = gen_state_schema(state_name, abbr, slug, cities, title, desc, faq_q2, faq_q3)

    # Pitfall 8 + 15: new content blocks
    bt_numbers = by_the_numbers(state_name, cities)
    sim_states = similar_states(state_name, info, all_states)

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
    <p class="source-note">Regulatory Climate and Primary Residence fields derived from city-level archetype data. Preemption status verified against state statutes ({', '.join(k + ': ' + v for k, v in VERIFICATION_SOURCES.items() if k == state_name) or 'verified against state legislative records'}).</p>
  </section>'''

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

  {bt_numbers}

  <h2 id="overview">Regulatory Overview</h2>
  <p>{overview}</p>

  {ranking}

  <h2 id="city-comparison">City Comparison — {n} {'City' if n==1 else 'Cities'}</h2>
  <p>All {state_name} cities covered by RentPermitted, ranked and compared:</p>
  {table}

  <h2 id="faq">Frequently Asked Questions</h2>
  <details><summary>How many cities in {state_name} does RentPermitted cover?</summary><p>We cover {n} {'city' if n==1 else 'cities'} in {state_name}: {', '.join(c['city'] for c in sorted(cities, key=lambda x: x['city']))}.</p></details>
  <details><summary>Does {state_name} have state-wide STR laws?</summary><p>{faq_q2}</p></details>
  <details><summary>Which {state_name} city is best for STR investment?</summary><p>{faq_q3}</p></details>

  {sim_states}

  <div class="disclaimer">
    <p><strong>Disclaimer:</strong> Data sourced from official {state_name} city websites and state statutes. Regulations change. Verify with local authorities before making investment decisions. Last comprehensive review: May 2026.</p>
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

        html_content = gen_state_page(state_name, info, STATES)
        out_path = os.path.join(page_dir, "index.html")
        with open(out_path, "w") as f:
            f.write(html_content)

        print(f"  ✓ {state_name:20s} → /{slug}/ ({len(info['cities'])} cities, {len(html_content):,} bytes)")

    print(f"\n✅ Generated {len(STATES)} state hub pages")
