# market-commentaries-transcript-summary

Checks a configurable list of YouTube channels daily (currently
[MacroVoices](https://www.youtube.com/@macrovoices7508)). When any channel posts a new video,
fetches its transcript and emails it.

## How it works

1. `.github/workflows/daily_check.yml` runs `agents/check_new_video.py` every day at 00:00 UTC
   (08:00 SGT) via GitHub Actions, plus supports manual runs (`workflow_dispatch`).
2. `config/channels.py` lists the channels to monitor (name + channel ID). Add more entries here
   to track additional channels — no other code changes needed.
3. For each channel, the script reads its YouTube RSS feed (no API key needed) and compares the
   latest video ID against that channel's entry in `data/last_video.json`.
4. If it's new, it fetches the transcript with `youtube-transcript-api` and emails it via Gmail
   SMTP (`shared/email_sender.py`, same pattern as `ai-momentum`/`weekly-market-recap`).
5. The workflow commits the updated `data/last_video.json` back to the repo so state persists
   across runs. `data/last_video.json` maps `channel_id -> last_seen_video_id`.

### Adding a channel

Find the channel ID (visit the channel page, view source, search for `"externalId"`) and add it
to `CHANNELS` in `config/channels.py`:

```python
CHANNELS = [
    {"name": "Macro Voices", "channel_id": "UCICRehoZjq3ZtAWgRJX118A"},
    {"name": "Some Other Channel", "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx"},
]
```

The next scheduled run will pick it up automatically (and will email the channel's current
latest video once, since it has no prior state — see note below).

## Required GitHub secrets

Set these in the repo's Settings → Secrets and variables → Actions (same values as `ai-momentum`):

- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `RECIPIENT_EMAIL`

## Known limitation: transcript fetching may get IP-blocked

YouTube blocks most cloud-provider IPs (including GitHub Actions runners) from the transcript
endpoint. When that happens, `check_new_video.py` still emails you the new-video notification
(title + link) with a note that the transcript wasn't available, instead of failing silently.

If this happens often and you want transcripts reliably, the fix is a rotating residential proxy
(e.g. [Webshare](https://www.webshare.io/)) passed into `YouTubeTranscriptApi(proxy_config=...)` —
see the [youtube-transcript-api README](https://github.com/jdepoix/youtube-transcript-api#working-around-ip-bans-requestblocked-or-ipblocked-exception).

## Local test run

```bash
pip install -r requirements.txt
GMAIL_USER=you@gmail.com GMAIL_APP_PASSWORD=xxxx RECIPIENT_EMAIL=you@gmail.com python agents/check_new_video.py
```

To force a test email even when there's no new video, temporarily edit `data/last_video.json`
to a different/older video ID before running.
