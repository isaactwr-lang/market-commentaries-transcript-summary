"""Transcript fetching with a fallback chain.

YouTube blocks most cloud-provider IPs (incl. GitHub Actions runners) from the
youtube-transcript-api endpoint. yt-dlp's Android-client caption extraction goes
through a different path and sometimes still works from the same IPs, so it's
tried second before giving up.
"""
from __future__ import annotations

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


def _via_youtube_transcript_api(video_id: str) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return "\n".join(snippet.text for snippet in transcript)
    except Exception as e:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")
        return None


def _via_yt_dlp(video_id: str) -> str | None:
    try:
        import yt_dlp

        ydl_opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

        captions = info.get("automatic_captions") or {}
        tracks = captions.get("en") or info.get("subtitles", {}).get("en") or []
        json_track = next((t for t in tracks if t.get("ext") == "json3"), None)
        if not json_track:
            logger.warning(f"yt-dlp found no json3 English captions for {video_id}")
            return None

        req = urllib.request.Request(json_track["url"], headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))

        words = [
            seg.get("utf8", "")
            for event in data.get("events", [])
            for seg in (event.get("segs") or [])
        ]
        text = " ".join("".join(words).split())
        return text or None
    except Exception as e:
        logger.warning(f"yt-dlp caption fetch failed for {video_id}: {e}")
        return None


def fetch_transcript(video_id: str) -> str | None:
    return _via_youtube_transcript_api(video_id) or _via_yt_dlp(video_id)
