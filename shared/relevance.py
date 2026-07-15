"""LLM-based market-relevance filter using Groq (same provider as ai-momentum)."""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM = """You decide whether a YouTube video belongs in a market-commentary digest for an \
investor audience. Include videos about markets, macro economics, monetary policy, interest \
rates, equities, credit, currencies, commodities, investment strategy, or company/sector \
outlooks with clear market implications. Exclude videos that are primarily about corporate \
culture, careers/recruiting, philanthropy, community/sports sponsorships, internal culture, \
or brand marketing with no substantive market or investment content, even if a bank or asset \
manager posted them.

Reply with strict JSON only: {"market_related": true or false, "reason": "<one short sentence>"}"""


def is_market_related(title: str, description: str) -> bool:
    """True if the video should be included. Fails open (returns True) if the classifier
    can't run — silently dropping a relevant video is worse than an occasional false positive."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — skipping relevance filter, including video")
        return True

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Title: {title}\n\nDescription: {description[:500]}"},
            ],
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        relevant = bool(result.get("market_related", True))
        logger.info(f"Relevance check -> {relevant} ({result.get('reason', '')})")
        return relevant
    except Exception as e:
        logger.warning(f"Relevance classification failed ({e}) — including video")
        return True
