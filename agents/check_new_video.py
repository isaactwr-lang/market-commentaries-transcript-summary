"""Daily check for new videos across monitored YouTube channels — fetches transcript and emails it."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.channels import CHANNELS
from shared.email_sender import send_email
from shared.relevance import is_market_related

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent.parent / "data" / "last_video.json"


def _feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def _latest_video(channel_id: str) -> dict:
    feed = feedparser.parse(_feed_url(channel_id))
    if not feed.entries:
        raise RuntimeError(f"RSS feed for {channel_id} returned no entries")
    entry = feed.entries[0]
    return {
        "id": entry.yt_videoid,
        "title": entry.title,
        "url": entry.link,
        "published": entry.published,
        "description": getattr(entry, "summary", ""),
    }


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text())


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _fetch_transcript(video_id: str) -> str | None:
    # YouTube blocks most cloud-provider IPs (incl. GitHub Actions runners) from
    # this endpoint — see IP-ban note in youtube-transcript-api's README. When
    # blocked we fall back to a transcript-unavailable email rather than failing.
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return "\n".join(snippet.text for snippet in transcript)
    except Exception as e:
        logger.warning(f"Transcript fetch failed for {video_id}: {e}")
        return None


def _build_email(channel_name: str, video: dict, transcript: str | None) -> tuple[str, str]:
    subject = f"New {channel_name} video: {video['title']}"
    if transcript:
        body_html = f"<pre style='white-space:pre-wrap;font-family:inherit'>{transcript}</pre>"
    else:
        body_html = "<p><em>Transcript unavailable (YouTube likely blocked this server's IP). Use the link above to watch/read captions directly.</em></p>"
    html = (
        f"<h2>{video['title']}</h2>"
        f"<p>Channel: {channel_name}</p>"
        f"<p><a href=\"{video['url']}\">{video['url']}</a></p>"
        f"<p>Published: {video['published']}</p>"
        f"<hr/>"
        f"{body_html}"
    )
    return subject, html


def _check_channel(channel: dict, state: dict) -> None:
    name, channel_id = channel["name"], channel["channel_id"]
    video = _latest_video(channel_id)
    last_seen = state.get(channel_id)

    if video["id"] == last_seen:
        logger.info(f"[{name}] No new video (latest is still {video['id']})")
        return

    logger.info(f"[{name}] New video detected: {video['id']} — {video['title']}")
    state[channel_id] = video["id"]  # advance regardless of relevance so we don't re-check it daily

    if not is_market_related(video["title"], video["description"]):
        logger.info(f"[{name}] Skipping (not market related): {video['title']}")
        return

    transcript = _fetch_transcript(video["id"])
    subject, html = _build_email(name, video, transcript)
    send_email(subject, html)


def main() -> None:
    state = _load_state()
    for channel in CHANNELS:
        try:
            _check_channel(channel, state)
        except Exception as e:
            logger.error(f"[{channel['name']}] Check failed: {e}")
    _save_state(state)


if __name__ == "__main__":
    main()
