"""LLM transcript summarization using Groq (same provider as ai-momentum)."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM = """You summarize finance/markets YouTube video transcripts into concise key points for \
a busy investor audience. Extract the concrete claims, forecasts, data points, and named \
entities (people, companies, assets, indicators) discussed — skip host banter, sponsor reads, \
and generic intros/outros.

Output 5-8 bullet points as clean HTML: a single <ul> containing <li> items only, each 1-2 \
sentences. No headers, no preamble, no markdown."""


def summarize_transcript(title: str, transcript: str) -> str | None:
    """Returns an HTML bullet-list summary, or None if summarization can't run (caller should
    fall back to the raw transcript rather than send an empty email)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — cannot summarize, falling back to raw transcript")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Video title: {title}\n\nTranscript:\n{transcript[:60000]}"},
            ],
            max_tokens=700,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Summarization failed ({e}) — falling back to raw transcript")
        return None
