"""Ticker-to-legislation exposure rationales for dashboard context.

These are thematic, curated mappings, NOT verified causal stock impact.
"""

from __future__ import annotations

# confidence: high = direct contractor/regulatory link, medium = sector adjacency, low = broad map
TICKER_RATIONALE: dict[str, dict[str, str | float]] = {
    # Aerospace / defense primes
    "BA": {
        "confidence": 0.85,
        "rationale": "Major aerospace contractor; space launch, satellites, and defense systems revenue.",
        "link_type": "direct",
    },
    "LMT": {
        "confidence": 0.9,
        "rationale": "Largest defense contractor; space systems, satellites, and missile defense programs.",
        "link_type": "direct",
    },
    "RTX": {
        "confidence": 0.85,
        "rationale": "Defense/aerospace conglomerate (Raytheon, Collins); space and missile systems.",
        "link_type": "direct",
    },
    "NOC": {
        "confidence": 0.85,
        "rationale": "Defense contractor with space, cyber, and autonomous systems lines.",
        "link_type": "direct",
    },
    "GD": {
        "confidence": 0.8,
        "rationale": "General Dynamics; submarine and space-related defense IT (GDIT).",
        "link_type": "direct",
    },
    "LHX": {
        "confidence": 0.75,
        "rationale": "Defense electronics and space communications (L3Harris).",
        "link_type": "direct",
    },
    "GE": {
        "confidence": 0.6,
        "rationale": "Aerospace engines and aviation systems; indirect space-launch exposure.",
        "link_type": "sector",
    },
    "PLTR": {
        "confidence": 0.7,
        "rationale": "Government/defense software; space and intelligence analytics contracts.",
        "link_type": "sector",
    },
    # Semiconductors
    "NVDA": {
        "confidence": 0.55,
        "rationale": "Chips used in satellite compute, AI workloads, and defense systems; indirect link.",
        "link_type": "supply_chain",
    },
    "AMD": {
        "confidence": 0.5,
        "rationale": "Semiconductor supplier for embedded and compute systems; indirect.",
        "link_type": "supply_chain",
    },
    "INTC": {
        "confidence": 0.5,
        "rationale": "Semiconductor supplier; possible space/defense embedded systems exposure.",
        "link_type": "supply_chain",
    },
    "AVGO": {
        "confidence": 0.5,
        "rationale": "Semiconductor and infrastructure chips; indirect space/defense supply chain.",
        "link_type": "supply_chain",
    },
    "QCOM": {
        "confidence": 0.45,
        "rationale": "Wireless/satellite communications chips; moderate indirect exposure.",
        "link_type": "supply_chain",
    },
    "ASML": {
        "confidence": 0.4,
        "rationale": "Semiconductor equipment; very indirect via chip supply chain.",
        "link_type": "supply_chain",
    },
    # Energy
    "XOM": {
        "confidence": 0.35,
        "rationale": "Included via broad energy sector map; weak direct link to space legislation.",
        "link_type": "sector",
    },
    "CVX": {
        "confidence": 0.35,
        "rationale": "Included via broad energy sector map; weak direct link to space legislation.",
        "link_type": "sector",
    },
    "COP": {
        "confidence": 0.35,
        "rationale": "Energy sector mapping; tangential at best to space policy votes.",
        "link_type": "sector",
    },
    "OXY": {
        "confidence": 0.35,
        "rationale": "Energy sector mapping; tangential at best to space policy votes.",
        "link_type": "sector",
    },
    "SLB": {
        "confidence": 0.3,
        "rationale": "Oilfield services; included in broad sector exposure list only.",
        "link_type": "sector",
    },
    "NEE": {
        "confidence": 0.3,
        "rationale": "Utility/renewables; broad energy sector mapping with weak bill linkage.",
        "link_type": "sector",
    },
    # Financials
    "JPM": {
        "confidence": 0.25,
        "rationale": "Broad financials map; no direct space-policy exposure; portfolio diversification likely.",
        "link_type": "sector",
    },
    "BAC": {
        "confidence": 0.25,
        "rationale": "Broad financials map; indirect macro exposure only.",
        "link_type": "sector",
    },
    "GS": {
        "confidence": 0.25,
        "rationale": "Broad financials map; indirect macro exposure only.",
        "link_type": "sector",
    },
    "MS": {
        "confidence": 0.25,
        "rationale": "Broad financials map; indirect macro exposure only.",
        "link_type": "sector",
    },
    # Big tech
    "META": {
        "confidence": 0.4,
        "rationale": "Satellite internet (e.g. AMZN-adjacent space comms ecosystem); moderate indirect.",
        "link_type": "sector",
    },
    "GOOG": {
        "confidence": 0.45,
        "rationale": "Cloud, AI, and potential space-data services; moderate indirect exposure.",
        "link_type": "sector",
    },
    "GOOGL": {
        "confidence": 0.45,
        "rationale": "Same as GOOG; cloud and space-adjacent technology exposure.",
        "link_type": "sector",
    },
    "AMZN": {
        "confidence": 0.55,
        "rationale": "AWS and Project Kuiper; major AI cloud and data-center operator subject to energy/regulatory scrutiny.",
        "link_type": "sector",
    },
    "MSFT": {
        "confidence": 0.75,
        "rationale": "Major AI investor (OpenAI); Azure AI cloud and data-center energy use central to AI environmental debates.",
        "link_type": "direct",
    },
    "META": {
        "confidence": 0.8,
        "rationale": "Social platform directly affected by TikTok bans, KOSA, and deepfake legislation; heavy AI ad-tech spend.",
        "link_type": "direct",
    },
    "SNAP": {
        "confidence": 0.7,
        "rationale": "Social media platform; competes with TikTok and subject to youth-safety / AI content moderation bills.",
        "link_type": "direct",
    },
    "PINS": {
        "confidence": 0.65,
        "rationale": "Social platform with AI-driven recommendations; youth-safety and content bills.",
        "link_type": "sector",
    },
    "NFLX": {
        "confidence": 0.55,
        "rationale": "Streaming/AI content generation; deepfake and copyright legislation (NO FAKES).",
        "link_type": "sector",
    },
    "ADBE": {
        "confidence": 0.65,
        "rationale": "Generative AI tools (Firefly); deepfake and copyright legislation exposure.",
        "link_type": "sector",
    },
    "EQIX": {
        "confidence": 0.7,
        "rationale": "Data-center REIT; AI environmental impact bills target data-center energy and water use.",
        "link_type": "direct",
    },
    "DLR": {
        "confidence": 0.7,
        "rationale": "Data-center REIT; direct exposure to AI infrastructure energy reporting requirements.",
        "link_type": "direct",
    },
    "VST": {
        "confidence": 0.6,
        "rationale": "Power generation for Texas data centers; AI energy impact legislation.",
        "link_type": "sector",
    },
    "CEG": {
        "confidence": 0.6,
        "rationale": "Nuclear/clean power supplier to data centers; AI energy demand narrative.",
        "link_type": "sector",
    },
    "SMCI": {
        "confidence": 0.75,
        "rationale": "AI server hardware manufacturer; direct beneficiary and target of AI infrastructure policy.",
        "link_type": "direct",
    },
    "AI": {
        "confidence": 0.5,
        "rationale": "Pure-play enterprise AI software; governance and federal AI R&D bills.",
        "link_type": "sector",
    },
    "SNOW": {
        "confidence": 0.5,
        "rationale": "Cloud data platform; AI governance and data-quality legislation.",
        "link_type": "sector",
    },
    "ORCL": {
        "confidence": 0.55,
        "rationale": "Enterprise cloud and AI services; data-center and governance exposure.",
        "link_type": "sector",
    },
    "RBLX": {
        "confidence": 0.65,
        "rationale": "Youth-focused platform; KOSA and online safety legislation.",
        "link_type": "direct",
    },
}


def get_ticker_context(ticker: str, bill_sector: str | None = None) -> dict:
    """Return exposure context for a ticker, with fallback for unmapped symbols."""
    info = TICKER_RATIONALE.get(ticker.upper())
    if info:
        return {
            "ticker": ticker.upper(),
            "confidence": info["confidence"],
            "rationale": info["rationale"],
            "link_type": info["link_type"],
            "affects_stock": _confidence_label(float(info["confidence"])),
        }
    return {
        "ticker": ticker.upper(),
        "confidence": 0.4,
        "rationale": (
            f"Mapped to {bill_sector or 'bill'} sector exposure list. "
            "Specific linkage not individually verified."
        ),
        "link_type": "sector",
        "affects_stock": "unclear",
    }


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "plausible_direct"
    if confidence >= 0.5:
        return "possible_indirect"
    if confidence >= 0.35:
        return "weak_thematic"
    return "unlikely_direct"
