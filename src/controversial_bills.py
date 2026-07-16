"""Curated controversial / high-salience bills and stock exposure mappings.

These are illustrative exposure maps for associational analysis — not exhaustive
or definitive claims about which securities a bill materially affects.
"""

from __future__ import annotations

# bill_id -> metadata + tickers that may have legislative exposure
CONTROVERSIAL_BILL_CATALOG: dict[str, dict] = {
    # Defense / foreign aid
    "118-hr-2670": {
        "title": "National Defense Authorization Act FY2024",
        "tags": ["defense", "military", "foreign_policy"],
        "salience": 1.0,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "LHX", "HII"],
        "sector": "defense",
    },
    "118-hr-815": {
        "title": "National Defense Authorization Act FY2024 (House)",
        "tags": ["defense", "military"],
        "salience": 0.95,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA"],
        "sector": "defense",
    },
    "118-s-4638": {
        "title": "National Defense Authorization Act FY2025 (Senate)",
        "tags": ["defense", "military"],
        "salience": 1.0,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "PLTR"],
        "sector": "defense",
    },
    "118-s-3776": {
        "title": "Israel Security Supplemental Appropriations",
        "tags": ["foreign_policy", "defense", "middle_east"],
        "salience": 1.0,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "IAI"],
        "sector": "defense",
    },
    # Tech / China
    "118-hr-7521": {
        "title": "Protecting Americans from Foreign Adversary Controlled Applications (TikTok)",
        "tags": ["ai", "tech", "china", "social_media", "society", "national_security"],
        "salience": 1.0,
        "tickers": ["META", "GOOG", "GOOGL", "SNAP", "PINS", "ORCL", "AMZN", "MSFT", "NVDA"],
        "sector": "ai_society",
    },
    "118-s-4368": {
        "title": "Foreign Adversary Controlled Applications Act (Senate)",
        "tags": ["ai", "tech", "china", "social_media", "society"],
        "salience": 1.0,
        "tickers": ["META", "GOOG", "GOOGL", "SNAP", "ORCL", "AMZN", "MSFT"],
        "sector": "ai_society",
    },
    # Healthcare / Social Security
    "118-hr-82": {
        "title": "Social Security Fairness Act (WEP/GPO repeal)",
        "tags": ["healthcare", "social_security", "retirement"],
        "salience": 0.9,
        "tickers": ["UNH", "HUM", "CVS", "CI", "ELV", "MOH"],
        "sector": "health_insurance",
    },
    # Energy / climate
    "118-hr-1": {
        "title": "Lower Energy Costs Act",
        "tags": ["energy", "climate", "oil_gas"],
        "salience": 0.85,
        "tickers": ["XOM", "CVX", "COP", "OXY", "SLB", "NEE", "ENPH"],
        "sector": "energy",
    },
    "118-s-659": {
        "title": "Energy Independence and Security Act amendments",
        "tags": ["energy", "climate"],
        "salience": 0.8,
        "tickers": ["XOM", "CVX", "COP", "NEE", "FSLR"],
        "sector": "energy",
    },
    # Financial regulation
    "118-s-2155": {
        "title": "Economic Growth, Regulatory Relief, and Consumer Protection Act",
        "tags": ["finance", "banking", "regulation"],
        "salience": 0.75,
        "tickers": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK"],
        "sector": "financials",
    },
    # Abortion / reproductive health
    "118-s-4445": {
        "title": "Women's Health Protection Act",
        "tags": ["healthcare", "abortion", "reproductive_rights"],
        "salience": 0.95,
        "tickers": ["PFE", "MRK", "JNJ", "CVS", "WBA", "TDOC"],
        "sector": "healthcare",
    },
    # Appropriations / shutdown politics
    "118-hr-10545": {
        "title": "Continuing Appropriations FY2025",
        "tags": ["appropriations", "budget", "government_shutdown"],
        "salience": 0.85,
        "tickers": ["LMT", "RTX", "LDOS", "BAH", "CACI"],
        "sector": "government_contractors",
    },
    # Immigration
    "118-hr-2": {
        "title": "Secure the Border Act",
        "tags": ["immigration", "border_security"],
        "salience": 0.9,
        "tickers": ["GEO", "CXW", "LDOS", "RTX", "LMT"],
        "sector": "security",
    },
    # Pharma / drug pricing
    "118-s-3": {
        "title": "Lower Costs, More Transparency Act",
        "tags": ["healthcare", "pharma", "drug_pricing"],
        "salience": 0.85,
        "tickers": ["PFE", "MRK", "ABBV", "JNJ", "BMY", "LLY", "UNH"],
        "sector": "pharma",
    },
    # AI / semiconductor
    "118-hr-7176": {
        "title": "CHIPS and Science Act implementation / related",
        "tags": ["ai", "tech", "semiconductors", "china", "environment"],
        "salience": 0.9,
        "tickers": ["NVDA", "AMD", "INTC", "TSM", "AVGO", "QCOM", "ASML", "SMCI", "MU"],
        "sector": "ai_hardware",
    },
    # AI — environmental / data-center impact
    "118-hr-7197": {
        "title": "Artificial Intelligence Environmental Impacts Act of 2024",
        "tags": ["ai", "environment", "climate", "data_centers", "energy", "society"],
        "salience": 1.0,
        "tickers": [
            "NVDA", "AMD", "MSFT", "GOOGL", "GOOG", "META", "AMZN", "ORCL",
            "NEE", "VST", "CEG", "EQIX", "DLR", "SMCI", "XOM", "CVX", "ENPH", "FSLR",
        ],
        "sector": "ai_infrastructure",
    },
    "118-s-3732": {
        "title": "Artificial Intelligence Environmental Impacts Act of 2024 (Senate)",
        "tags": ["ai", "environment", "climate", "data_centers", "energy", "society"],
        "salience": 1.0,
        "tickers": [
            "NVDA", "AMD", "MSFT", "GOOGL", "GOOG", "META", "AMZN",
            "NEE", "VST", "CEG", "EQIX", "DLR", "SMCI", "XOM", "CVX",
        ],
        "sector": "ai_infrastructure",
    },
    # AI — deepfakes / societal harm
    "118-s-2691": {
        "title": "NO FAKES Act of 2024",
        "tags": ["ai", "deepfakes", "society", "copyright", "privacy"],
        "salience": 0.95,
        "tickers": ["META", "GOOGL", "GOOG", "SNAP", "PINS", "NFLX", "DIS", "WBD", "ADBE", "TTWO", "RBLX"],
        "sector": "ai_society",
    },
    "118-s-3787": {
        "title": "TAKE IT DOWN Act",
        "tags": ["ai", "deepfakes", "society", "privacy", "children"],
        "salience": 0.95,
        "tickers": ["META", "GOOGL", "GOOG", "SNAP", "PINS", "RBLX", "TTWO", "NFLX"],
        "sector": "ai_society",
    },
    "118-s-1993": {
        "title": "DEFIANCE Act (deepfake intimate images)",
        "tags": ["ai", "deepfakes", "society", "privacy"],
        "salience": 0.9,
        "tickers": ["META", "GOOGL", "GOOG", "SNAP", "ADBE", "NFLX"],
        "sector": "ai_society",
    },
    # AI — kids / platform safety
    "118-s-4178": {
        "title": "Kids Online Safety Act (KOSA)",
        "tags": ["ai", "society", "children", "social_media", "mental_health"],
        "salience": 1.0,
        "tickers": ["META", "GOOGL", "GOOG", "SNAP", "PINS", "RBLX", "TTWO", "NFLX", "MSFT"],
        "sector": "ai_society",
    },
    # AI — federal R&D / governance
    "118-hr-8834": {
        "title": "CREATE AI Act of 2024",
        "tags": ["ai", "research", "national_security", "governance"],
        "salience": 0.9,
        "tickers": ["NVDA", "AMD", "MSFT", "GOOGL", "GOOG", "META", "PLTR", "AI", "PATH", "SNOW", "CRM"],
        "sector": "ai_platforms",
    },
    # Ukraine / foreign aid
    "118-hr-8035": {
        "title": "Ukraine Security Supplemental Appropriations",
        "tags": ["foreign_policy", "defense", "ukraine"],
        "salience": 1.0,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "PLTR"],
        "sector": "defense",
    },
    "118-hr-4755": {
        "title": "Department of Defense Appropriations Act",
        "tags": ["defense", "appropriations"],
        "salience": 0.9,
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "LDOS", "BAH"],
        "sector": "defense",
    },
    # Gun policy
    "118-s-3369": {
        "title": "Assault Weapons Ban of 2023",
        "tags": ["guns", "public_safety"],
        "salience": 0.95,
        "tickers": ["RGR", "SWBI", "OLN", "VSTO", "SWK"],
        "sector": "firearms",
    },
    "118-hr-4639": {
        "title": "Federal Firearms License Reform Act",
        "tags": ["guns", "regulation"],
        "salience": 0.85,
        "tickers": ["RGR", "SWBI", "VSTO", "OLN"],
        "sector": "firearms",
    },
    # Crypto / digital assets
    "118-s-2281": {
        "title": "Digital Asset Anti-Money Laundering Act",
        "tags": ["crypto", "finance", "regulation"],
        "salience": 0.9,
        "tickers": ["COIN", "MARA", "RIOT", "MSTR", "HOOD"],
        "sector": "crypto",
    },
    "118-hr-4763": {
        "title": "Financial Innovation and Technology for the 21st Century Act (FIT21)",
        "tags": ["ai", "crypto", "finance", "tech", "governance"],
        "salience": 0.95,
        "tickers": ["COIN", "HOOD", "SQ", "PYPL", "MSTR", "NVDA", "MSFT"],
        "sector": "ai_finance",
    },
    # FAA / aviation
    "118-hr-3935": {
        "title": "FAA Reauthorization Act of 2024",
        "tags": ["transportation", "aviation", "regulation"],
        "salience": 0.85,
        "tickers": ["BA", "LMT", "RTX", "GE", "DAL", "UAL", "AAL"],
        "sector": "aviation",
    },
    # Farm bill / agriculture subsidies
    "118-hr-4368": {
        "title": "Agriculture, Rural Development, Food and Drug Administration Appropriations",
        "tags": ["agriculture", "appropriations", "food_policy"],
        "salience": 0.8,
        "tickers": ["DE", "CTVA", "MOS", "ADM", "BG"],
        "sector": "agriculture",
    },
    # Labor / union organizing
    "118-s-4194": {
        "title": "Protecting the Right to Organize Act (PRO Act)",
        "tags": ["labor", "unions", "workplace"],
        "salience": 0.9,
        "tickers": ["AMZN", "WMT", "TGT", "SBUX", "FDX", "UPS"],
        "sector": "retail_logistics",
    },
    # 119th Congress
    "119-hr-6329": {
        "title": "Information Quality Assurance Act of 2025",
        "summary": (
            "Would set federal standards for reviewing and assuring the quality of "
            "information used in government decisions, with a focus on data and AI-driven systems."
        ),
        "tags": ["ai", "data", "regulation", "society", "governance"],
        "salience": 0.9,
        "tickers": ["NVDA", "MSFT", "GOOGL", "GOOG", "META", "PLTR", "AI", "SNOW", "DDOG", "CRM", "ORCL"],
        "sector": "ai_governance",
    },
    "119-hr-3424": {
        "title": "SPACE Act of 2025",
        "summary": (
            "Would update U.S. space policy and federal programs tied to civil, commercial, "
            "and national security space activities, including oversight of space missions and assets."
        ),
        "tags": ["space", "defense", "aerospace", "technology"],
        "salience": 0.95,
        "tickers": [
            "BA", "LMT", "RTX", "NOC", "GD", "PLTR", "LHX", "GE",
            "NVDA", "AMD", "INTC", "AVGO", "QCOM", "ASML",
            "XOM", "CVX", "COP", "OXY", "SLB", "NEE",
            "JPM", "BAC", "GS", "MS", "META", "GOOG", "GOOGL", "AMZN",
        ],
        "sector": "aerospace",
    },
    "119-hr-3425": {
        "title": "Personnel Oversight and Shift Tracking Act of 2025 (POST Act)",
        "summary": (
            "Would require the Federal Protective Service to improve tracking and accountability "
            "of contract security guards who protect federal buildings."
        ),
        "tags": ["homeland_security", "government_contractors", "security", "society"],
        "salience": 0.85,
        "tickers": ["LDOS", "RTX", "LMT", "BAH", "CACI", "GEO", "MSA"],
        "sector": "security_contractors",
    },
    "119-hr-4758": {
        "title": "Homeowner Energy Freedom Act",
        "summary": (
            "Would repeal Inflation Reduction Act programs that subsidize home electrification, "
            "energy-efficiency upgrades, and adoption of stricter building energy codes."
        ),
        "tags": ["energy", "climate", "environment", "housing"],
        "salience": 0.9,
        "tickers": ["XOM", "CVX", "COP", "OXY", "SLB", "NEE", "ENPH", "FSLR", "TSLA"],
        "sector": "energy",
    },
    "119-hr-5348": {
        "title": "Social Security Child Protection Act of 2025",
        "summary": (
            "Would let the Social Security Administration issue a new Social Security number to "
            "children under 14 when their card was lost or stolen while being mailed to them."
        ),
        "tags": ["social_security", "children", "society", "identity", "government"],
        "salience": 0.85,
        "tickers": ["LDOS", "BAH", "MSFT", "ORCL", "ACN", "PANW", "UNH"],
        "sector": "gov_it_identity",
    },
}


# Tags used for AI / environmental / societal-impact focus in stock timing analysis
AI_FOCUS_TAGS: frozenset[str] = frozenset({
    "ai",
    "environment",
    "climate",
    "data_centers",
    "deepfakes",
    "society",
    "children",
    "mental_health",
    "social_media",
    "governance",
})


def all_controversial_bill_ids() -> list[str]:
    return list(CONTROVERSIAL_BILL_CATALOG.keys())


def bills_matching_tags(tags: set[str] | frozenset[str]) -> list[str]:
    """Return bill_ids whose controversy tags intersect the given tag set."""
    wanted = set(tags)
    return [
        bill_id
        for bill_id, meta in CONTROVERSIAL_BILL_CATALOG.items()
        if wanted.intersection(meta.get("tags", []))
    ]


def ai_focus_bill_ids() -> list[str]:
    return bills_matching_tags(AI_FOCUS_TAGS)
