"""
Industry Knowledge Base
=======================
Domain expertise injected into the AI analysis pipeline. Each industry profile
carries the KPIs that matter, typical benchmark ranges, risk frameworks, and
the chart types that best communicate that industry's data.

Used by analyzer.py:
  1. Haiku classifies the document's industry (fast pass)
  2. The matching profile is injected into Sonnet's system prompt (deep pass)
"""

INDUSTRY_PROFILES = {
    "retail_ecommerce": {
        "name": "Retail & E-Commerce",
        "icon": "🛍️",
        "key_kpis": [
            "Total revenue / GMV", "Same-store sales growth", "Average order value (AOV)",
            "Conversion rate", "Gross margin", "Inventory turnover", "Sell-through rate",
            "Customer acquisition cost (CAC)", "Repeat purchase rate", "Return rate",
        ],
        "benchmarks": (
            "Healthy gross margin: 25-50% (general retail), 50-65% (apparel/beauty). "
            "E-commerce conversion rate: 2-3% average, >4% strong. AOV growth >5% YoY is good. "
            "Inventory turnover: 4-8x/year healthy for most retail; <2x signals overstock. "
            "Return rates: 8-10% in-store, 20-30% online apparel. Repeat purchase rate >25% is strong. "
            "MoM revenue swings beyond ±15% outside holiday seasons warrant investigation."
        ),
        "risk_framework": (
            "Watch for: inventory obsolescence, margin compression from discounting, "
            "category concentration (one category >50% of revenue), seasonal dependency, "
            "rising CAC vs LTV, supply chain disruption, shrinkage/stock-outs."
        ),
        "recommended_charts": ["bar (category revenue)", "line (sales trend)", "pie (revenue mix)"],
    },
    "finance_banking": {
        "name": "Finance & Banking",
        "icon": "🏦",
        "key_kpis": [
            "Net interest margin (NIM)", "Return on equity (ROE)", "Return on assets (ROA)",
            "Efficiency ratio", "Non-performing loan (NPL) ratio", "Capital adequacy ratio (CAR)",
            "Loan-to-deposit ratio", "Cost of risk", "Assets under management (AUM)",
        ],
        "benchmarks": (
            "Healthy ROE: 10-15% for banks. NIM: 3-4% typical for commercial banks. "
            "Efficiency ratio <60% is good (lower is better). NPL ratio <2% healthy, >5% distressed. "
            "CAR regulatory minimum ~10.5% (Basel III), strong banks hold 13-15%. "
            "Loan-to-deposit ratio 80-90% balanced; >100% indicates liquidity strain."
        ),
        "risk_framework": (
            "Watch for: credit risk concentration, liquidity mismatches, interest-rate sensitivity, "
            "regulatory capital shortfalls, deteriorating asset quality, fraud indicators, "
            "covenant breaches, currency exposure."
        ),
        "recommended_charts": ["line (trend of ratios)", "bar (portfolio breakdown)", "pie (asset mix)"],
    },
    "corporate_financial": {
        "name": "Corporate Finance & FP&A",
        "icon": "📈",
        "key_kpis": [
            "Revenue growth (YoY/QoQ)", "Gross margin", "EBITDA margin", "Operating margin",
            "Net income", "Free cash flow", "Burn rate / runway", "Working capital",
            "DSO/DPO/DIO", "Debt-to-equity",
        ],
        "benchmarks": (
            "Gross margin varies by sector: software 70-85%, services 30-50%, hardware 20-40%. "
            "EBITDA margin >15% generally healthy; >25% strong. Revenue growth >10% YoY solid for mature firms, "
            ">30% for growth-stage. Current ratio 1.5-3.0 healthy. Debt-to-equity <2.0 typical; "
            "DSO <45 days good for B2B. FCF margin >10% is strong."
        ),
        "risk_framework": (
            "Watch for: declining margins across periods, negative operating cash flow with positive net income "
            "(earnings quality), customer concentration >20% of revenue, rising leverage, "
            "shrinking runway (<12 months), one-time items masking trends."
        ),
        "recommended_charts": ["bar (P&L lines)", "line (quarterly trend)", "pie (revenue segments)"],
    },
    "healthcare": {
        "name": "Healthcare & Life Sciences",
        "icon": "🏥",
        "key_kpis": [
            "Patient volume / admissions", "Average length of stay (ALOS)", "Bed occupancy rate",
            "Readmission rate (30-day)", "Payer mix", "Revenue per patient", "Operating margin",
            "Days in accounts receivable", "Claim denial rate", "Patient satisfaction (HCAHPS/NPS)",
        ],
        "benchmarks": (
            "Hospital operating margin: 1-4% typical (thin); >5% strong. Bed occupancy 65-85% optimal. "
            "30-day readmission <15% target (US CMS penalizes >~16%). ALOS 4-5 days typical acute care. "
            "Claim denial rate <5% good, >10% problematic. Days in AR <45 healthy."
        ),
        "risk_framework": (
            "Watch for: payer mix shifting to lower-reimbursement sources, rising denial rates, "
            "compliance/HIPAA exposure, staffing shortages and overtime costs, readmission penalties, "
            "supply cost inflation, patient-safety indicators."
        ),
        "recommended_charts": ["line (volume trend)", "bar (department metrics)", "pie (payer mix)"],
    },
    "technology_saas": {
        "name": "Technology & SaaS",
        "icon": "💻",
        "key_kpis": [
            "ARR / MRR", "ARR growth rate", "Net revenue retention (NRR)", "Gross revenue retention",
            "Churn rate", "CAC payback period", "LTV:CAC ratio", "Rule of 40", "Gross margin",
            "Burn multiple", "DAU/MAU engagement",
        ],
        "benchmarks": (
            "SaaS gross margin: 70-85%. NRR >110% excellent, 100-110% good, <90% concerning. "
            "Monthly logo churn <1% enterprise, <3% SMB acceptable. LTV:CAC >3x healthy. "
            "CAC payback <12 months strong, <18 acceptable. Rule of 40 (growth% + FCF margin%) >40 is elite. "
            "Burn multiple <1.5x efficient, >2.5x inefficient."
        ),
        "risk_framework": (
            "Watch for: decelerating ARR growth with steady burn, NRR decline, customer concentration, "
            "rising churn cohorts, security/uptime incidents, technical debt signals, "
            "competitive pricing pressure."
        ),
        "recommended_charts": ["line (MRR/ARR trend)", "bar (cohort metrics)", "pie (revenue by plan)"],
    },
    "manufacturing": {
        "name": "Manufacturing & Industrial",
        "icon": "🏭",
        "key_kpis": [
            "Overall equipment effectiveness (OEE)", "Production yield / first-pass yield",
            "Capacity utilization", "Scrap/defect rate", "On-time delivery", "Inventory turns",
            "Cost per unit", "Downtime hours", "Safety incidents (TRIR)", "Order backlog",
        ],
        "benchmarks": (
            "World-class OEE: 85%+; typical: 60%. First-pass yield >95% strong. "
            "Capacity utilization 75-85% healthy (>90% leaves no maintenance headroom). "
            "On-time delivery >95% expected. Defect rate <1% good for discrete manufacturing. "
            "TRIR <1.0 strong safety record; industry average ~2.8."
        ),
        "risk_framework": (
            "Watch for: rising scrap/rework, unplanned downtime trends, single-supplier dependency, "
            "raw-material price exposure, safety incident clusters, aging equipment capex needs, "
            "backlog erosion."
        ),
        "recommended_charts": ["line (OEE/yield trend)", "bar (downtime by cause)", "pie (cost breakdown)"],
    },
    "real_estate": {
        "name": "Real Estate & Property",
        "icon": "🏢",
        "key_kpis": [
            "Occupancy rate", "Net operating income (NOI)", "Cap rate", "Rent per sq ft",
            "Tenant retention rate", "Loan-to-value (LTV)", "Debt service coverage ratio (DSCR)",
            "Same-property NOI growth", "Lease expiration schedule",
        ],
        "benchmarks": (
            "Healthy occupancy: >92% multifamily, >85% office (post-2020 office often 70-85%). "
            "Cap rates: 4-6% prime residential/industrial, 6-9% secondary office/retail. "
            "DSCR >1.25x required by most lenders; >1.5x comfortable. LTV <70% conventional. "
            "Tenant retention >70% good. NOI growth 2-4%/yr typical stabilized."
        ),
        "risk_framework": (
            "Watch for: lease rollover concentration, rising vacancy, DSCR compression from rate resets, "
            "deferred maintenance, market oversupply, tenant credit deterioration."
        ),
        "recommended_charts": ["bar (NOI by property)", "line (occupancy trend)", "pie (tenant mix)"],
    },
    "legal_contracts": {
        "name": "Legal & Contracts",
        "icon": "⚖️",
        "key_kpis": [
            "Contract value", "Term length & renewal dates", "Liability caps", "Indemnification scope",
            "Termination rights & notice periods", "Payment terms", "SLA commitments",
            "Governing law & dispute resolution", "Auto-renewal clauses",
        ],
        "benchmarks": (
            "Standard liability caps: 12 months of fees (services), 1-2x contract value. "
            "Payment terms: Net 30 standard, Net 60-90 favors buyer. Notice for termination: 30-90 days typical. "
            "Auto-renewal windows commonly require 30-60 day opt-out notice — a frequent trap. "
            "Unlimited liability, one-sided indemnities, and unilateral price increases are red flags."
        ),
        "risk_framework": (
            "Watch for: uncapped liability, broad indemnification, IP assignment overreach, "
            "auto-renewal traps, missing termination-for-convenience, ambiguous SLAs without remedies, "
            "unfavorable governing law, missing confidentiality/data-protection terms."
        ),
        "recommended_charts": ["bar (obligations by party)", "line (payment schedule)"],
    },
    "hr_recruiting": {
        "name": "HR & Talent",
        "icon": "👥",
        "key_kpis": [
            "Headcount & growth", "Attrition/turnover rate", "Time to hire", "Cost per hire",
            "Offer acceptance rate", "eNPS / engagement score", "Diversity ratios",
            "Revenue per employee", "Absenteeism rate", "Training hours per employee",
        ],
        "benchmarks": (
            "Healthy annual voluntary attrition: 10-15% (tech ~13%, retail/hospitality 30-60% normal). "
            "Time to hire: 30-45 days typical, <30 strong. Offer acceptance >85% good. "
            "eNPS >20 good, >50 excellent. Revenue per employee varies: $150-200k services, $300k+ SaaS."
        ),
        "risk_framework": (
            "Watch for: attrition spikes in key teams, manager-level turnover, compression in offer "
            "acceptance (comp competitiveness), engagement decline trends, single-person dependencies, "
            "compliance gaps in policies."
        ),
        "recommended_charts": ["line (headcount/attrition trend)", "bar (dept breakdown)", "pie (workforce mix)"],
    },
    "education": {
        "name": "Education & Academia",
        "icon": "🎓",
        "key_kpis": [
            "Enrollment & growth", "Retention/persistence rate", "Graduation/completion rate",
            "Student-teacher ratio", "Cost per student", "Tuition revenue", "Grant funding",
            "Assessment scores", "Course completion rate (online)",
        ],
        "benchmarks": (
            "First-year retention: >80% strong for universities (US avg ~76%). 6-year graduation >60% good. "
            "Student-teacher ratio 15-20:1 typical K-12, 10-15:1 higher ed. "
            "Online course completion 60-80% for paid programs (MOOCs much lower, 5-15%)."
        ),
        "risk_framework": (
            "Watch for: enrollment decline trends, discount-rate creep (tuition discounting >50%), "
            "grant dependency, accreditation risks, achievement gaps across cohorts."
        ),
        "recommended_charts": ["line (enrollment trend)", "bar (scores by cohort)", "pie (funding sources)"],
    },
    "logistics_supply_chain": {
        "name": "Logistics & Supply Chain",
        "icon": "🚚",
        "key_kpis": [
            "On-time delivery (OTD)", "Perfect order rate", "Freight cost per unit", "Fleet utilization",
            "Inventory accuracy", "Order cycle time", "Fill rate", "Cost per mile/km",
            "Warehouse capacity utilization", "Damage/loss rate",
        ],
        "benchmarks": (
            "OTD >95% expected, >98% world-class. Perfect order rate >90% good. Fill rate >97% strong. "
            "Inventory accuracy >98% with cycle counting. Fleet utilization 80-90% optimal. "
            "Freight cost 6-10% of revenue typical for shippers."
        ),
        "risk_framework": (
            "Watch for: carrier concentration, fuel price exposure, OTD deterioration, "
            "capacity constraints in peak season, customs/regulatory delays, rising detention/demurrage."
        ),
        "recommended_charts": ["line (OTD trend)", "bar (cost by lane/region)", "pie (mode mix)"],
    },
    "energy_utilities": {
        "name": "Energy & Utilities",
        "icon": "⚡",
        "key_kpis": [
            "Capacity factor", "Availability factor", "LCOE (levelized cost of energy)",
            "SAIDI/SAIFI (outage metrics)", "Peak demand", "Transmission losses",
            "Renewable mix %", "Rate base growth", "Heat rate",
        ],
        "benchmarks": (
            "Capacity factors: nuclear ~92%, combined-cycle gas 50-60%, onshore wind 35-45%, solar 20-30%. "
            "Transmission & distribution losses <6% good. SAIDI <100 minutes/year strong reliability. "
            "Utility allowed ROE typically 9-10%."
        ),
        "risk_framework": (
            "Watch for: regulatory rate-case outcomes, fuel price volatility, aging infrastructure, "
            "extreme-weather exposure, stranded-asset risk in fossil portfolios, grid stability."
        ),
        "recommended_charts": ["line (output/demand trend)", "bar (generation by source)", "pie (energy mix)"],
    },
    "hospitality_food": {
        "name": "Hospitality & Food Service",
        "icon": "🏨",
        "key_kpis": [
            "RevPAR (revenue per available room)", "ADR (average daily rate)", "Occupancy rate",
            "Table turnover rate", "Food cost %", "Labor cost %", "Average check size",
            "Customer satisfaction / review scores", "Prime cost",
        ],
        "benchmarks": (
            "Hotel occupancy 65-75% healthy. Restaurant food cost 28-35% of sales; labor 25-35%; "
            "prime cost (food+labor) <60-65% target. Restaurant profit margin 3-9% typical. "
            "RevPAR growth above local market index indicates share gain."
        ),
        "risk_framework": (
            "Watch for: rising food/labor cost ratios, seasonality dependence, review score decline, "
            "staff turnover (industry runs 70%+), local competition saturation."
        ),
        "recommended_charts": ["line (occupancy/RevPAR trend)", "bar (revenue by outlet)", "pie (cost structure)"],
    },
    "marketing_media": {
        "name": "Marketing & Media",
        "icon": "📣",
        "key_kpis": [
            "ROAS / ROI", "CPM/CPC/CPA", "Conversion rate", "CTR", "Engagement rate",
            "Reach & impressions", "Email open/click rates", "Brand awareness lift",
            "Marketing-sourced pipeline", "Share of voice",
        ],
        "benchmarks": (
            "ROAS >4:1 strong, 2-3:1 break-even territory for many retailers. "
            "Search CTR 3-5% good; display 0.5-1%. Email open rate 20-25% average, CTR 2-3%. "
            "Social engagement rate 1-3% typical, >5% excellent. CPA must be < gross profit per order."
        ),
        "risk_framework": (
            "Watch for: rising CAC/CPA trends, channel over-dependence, attribution blind spots, "
            "creative fatigue (declining CTR), audience saturation, brand-safety issues."
        ),
        "recommended_charts": ["bar (channel performance)", "line (campaign trend)", "pie (budget allocation)"],
    },
    "insurance": {
        "name": "Insurance",
        "icon": "🛡️",
        "key_kpis": [
            "Combined ratio", "Loss ratio", "Expense ratio", "Premium growth",
            "Retention/renewal rate", "Claims frequency & severity", "Reserve adequacy", "Float yield",
        ],
        "benchmarks": (
            "Combined ratio <100% means underwriting profit; 95-98% typical for good P&C carriers. "
            "Loss ratio 60-70% typical; expense ratio 25-30%. Policy retention >85% strong. "
            "Premium growth above market ~5%/yr indicates share gain."
        ),
        "risk_framework": (
            "Watch for: reserve deficiencies, catastrophe exposure concentration, loss-ratio deterioration, "
            "fraud patterns in claims, regulatory capital strain, reinsurance cost spikes."
        ),
        "recommended_charts": ["line (combined ratio trend)", "bar (claims by line)", "pie (premium mix)"],
    },
    "facilities_services": {
        "name": "Facilities Services & RFP Analysis",
        "icon": "🧹",
        "key_kpis": [
            "Scope of work (services in/out)", "Cleanable square footage", "Facility count & locations",
            "Shift coverage & staffing plan (FTE per sq ft)", "Contract term & option years",
            "Estimated contract value / ceiling", "SLA response & inspection thresholds",
            "Past-performance requirements (CPARS, references)", "Small-business set-aside / socioeconomic status",
            "Wage determination (Davis-Bacon / SCA)", "Insurance & bonding requirements",
            "Key personnel & staffing qualifications", "Transition-in / phase-in period",
            "Liquidated damages & deduction schedule", "Green cleaning / LEED requirements",
        ],
        "benchmarks": (
            "Janitorial pricing benchmarks (US, 2024): $0.05-$0.20 per sq ft per month for standard commercial; "
            "$0.15-$0.30 for medical/lab; government contracts often at the lower end due to volume. "
            "Standard cleaner productivity: 3,500-4,500 sq ft/hour for general office, 2,000-3,000 for restrooms/medical. "
            "Typical contract term: 1 base year + 4 option years (federal), 3-5 years commercial. "
            "SCA / Davis-Bacon prevailing wages apply to most federal facilities work — always priced separately. "
            "Standard insurance: $1M general liability, $1M auto, workers' comp per state. "
            "SLAs: 2-4 hour response for urgent, next-business-day for standard requests. "
            "Past-performance requirements typically 3-5 references of similar scope/value within last 3-5 years."
        ),
        "risk_framework": (
            "Watch for: unlimited or uncapped liability, one-sided indemnification, liquidated damages tied to "
            "subjective quality scores, unclear scope boundaries ('other duties as assigned'), unfunded "
            "transition/phase-in periods, key-personnel lock-in clauses, Davis-Bacon/SCA exposure not "
            "reflected in pricing, aggressive small-business subcontracting targets, short response-time SLAs "
            "without after-hours pricing, bonding/insurance requirements exceeding standard $1M, "
            "ambiguous performance-based deductions, unrealistic staffing ratios implied by scope, "
            "past-performance thresholds the bidder cannot meet, mandatory site visits missed."
        ),
        "recommended_charts": [
            "bar (requirements by category: scope, admin, compliance)",
            "pie (risk-flag distribution: pricing, legal, operational)",
            "line (deadline timeline: questions due, proposal due, award)",
        ],
    },
    "general": {
        "name": "General Business",
        "icon": "📄",
        "key_kpis": [
            "Revenue & growth", "Costs & margins", "Cash flow", "Key counts/volumes",
            "Dates & deadlines", "Named parties & amounts",
        ],
        "benchmarks": (
            "Apply general business judgment: flag double-digit declines, margin compression, "
            "concentration risks, missed deadlines, and unusual variances vs stated targets."
        ),
        "risk_framework": (
            "Watch for: trends moving against stated goals, missing or inconsistent figures, "
            "obligations with near-term deadlines, dependencies on single parties."
        ),
        "recommended_charts": ["bar", "line", "pie"],
    },
}

# Aliases the classifier may emit → canonical profile keys
INDUSTRY_ALIASES = {
    "retail": "retail_ecommerce", "ecommerce": "retail_ecommerce", "e-commerce": "retail_ecommerce",
    "cpg": "retail_ecommerce", "consumer goods": "retail_ecommerce",
    "banking": "finance_banking", "finance": "finance_banking", "fintech": "finance_banking",
    "investment": "finance_banking", "wealth": "finance_banking",
    "corporate": "corporate_financial", "fp&a": "corporate_financial", "accounting": "corporate_financial",
    "financial statement": "corporate_financial",
    "medical": "healthcare", "pharma": "healthcare", "biotech": "healthcare", "hospital": "healthcare",
    "tech": "technology_saas", "saas": "technology_saas", "software": "technology_saas",
    "technology": "technology_saas", "startup": "technology_saas",
    "industrial": "manufacturing", "factory": "manufacturing",
    "property": "real_estate", "construction": "real_estate", "reit": "real_estate",
    "legal": "legal_contracts", "contract": "legal_contracts", "law": "legal_contracts",
    "hr": "hr_recruiting", "human resources": "hr_recruiting", "talent": "hr_recruiting",
    "recruiting": "hr_recruiting", "resume": "hr_recruiting",
    "academic": "education", "school": "education", "university": "education",
    "logistics": "logistics_supply_chain", "supply chain": "logistics_supply_chain",
    "transportation": "logistics_supply_chain", "shipping": "logistics_supply_chain",
    "energy": "energy_utilities", "utilities": "energy_utilities", "oil": "energy_utilities",
    "renewables": "energy_utilities",
    "hospitality": "hospitality_food", "restaurant": "hospitality_food", "hotel": "hospitality_food",
    "food": "hospitality_food", "travel": "hospitality_food",
    "marketing": "marketing_media", "advertising": "marketing_media", "media": "marketing_media",
    "agency": "marketing_media",
    "facilities": "facilities_services", "facility": "facilities_services",
    "facilities services": "facilities_services", "facility services": "facilities_services",
    "janitorial": "facilities_services", "custodial": "facilities_services",
    "cleaning": "facilities_services", "building services": "facilities_services",
    "building maintenance": "facilities_services", "property services": "facilities_services",
    "grounds maintenance": "facilities_services", "landscaping services": "facilities_services",
}


def resolve_industry(raw: str) -> str:
    """Map a free-text industry label to a canonical profile key."""
    if not raw:
        return "general"
    key = raw.strip().lower().replace("&", "and")
    if key in INDUSTRY_PROFILES:
        return key
    key_norm = key.replace("_", " ").replace("-", " ")
    for alias, canonical in INDUSTRY_ALIASES.items():
        if alias in key_norm:
            return canonical
    return "general"


def get_profile(industry_key: str) -> dict:
    return INDUSTRY_PROFILES.get(industry_key, INDUSTRY_PROFILES["general"])


def build_industry_prompt_block(industry_key: str) -> str:
    """Render an industry profile as a prompt block for the deep-analysis pass."""
    p = get_profile(industry_key)
    return f"""INDUSTRY CONTEXT — {p['name']}
You are analyzing this document as a senior {p['name']} analyst with 15+ years of domain experience.

KPIs that matter most in this industry:
{chr(10).join('- ' + k for k in p['key_kpis'])}

Benchmark knowledge (use to judge whether figures in the document are strong, average, or weak):
{p['benchmarks']}

Industry risk framework:
{p['risk_framework']}

When extracting metrics, prefer the KPIs above. When writing insights and recommendations,
compare the document's figures against these benchmarks explicitly (e.g. "gross margin of 31%
sits at the low end of the healthy 25-50% retail range"). Flag anything the risk framework
highlights."""
