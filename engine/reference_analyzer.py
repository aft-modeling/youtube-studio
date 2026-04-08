import re
import json
import anthropic
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_metadata(video_id: str) -> dict:
    """Extract video metadata using yt-dlp (no download)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_check_certificates": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    duration_seconds = info.get("duration", 0)
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60

    return {
        "title": info.get("title", "Unknown"),
        "description": info.get("description", "")[:1000],
        "duration": f"{minutes}:{seconds:02d}",
        "duration_seconds": duration_seconds,
        "view_count": info.get("view_count", 0),
        "tags": info.get("tags", []),
        "channel": info.get("uploader", "Unknown"),
    }


def _get_transcript(video_id: str) -> str | None:
    """Get transcript using youtube-transcript-api v1.x."""
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)

        transcript = None

        # 1. Try English manual transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except Exception:
            pass

        # 2. Try English auto-generated transcript
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            except Exception:
                pass

        # 3. Try translating any available transcript to English
        if transcript is None:
            for t in transcript_list:
                try:
                    transcript = t.translate("en")
                    break
                except Exception:
                    continue

        if transcript is None:
            return None

        fetched = transcript.fetch()
        lines = [snippet.text for snippet in fetched.snippets]
        return " ".join(lines)

    except Exception:
        # Fallback: try direct fetch (defaults to English)
        try:
            fetched = api.fetch(video_id)
            lines = [snippet.text for snippet in fetched.snippets]
            return " ".join(lines)
        except Exception:
            return None


async def _summarize_transcript(transcript: str) -> str:
    """Summarize a long transcript using Claude to stay within token limits."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Summarize this YouTube video transcript into a detailed outline. Keep all key points, examples, data, and arguments. This summary will be used as reference material for writing a new script on the same topic.

TRANSCRIPT:
{transcript[:30000]}

Provide a detailed summary (1500-2000 words) that captures the structure, main arguments, examples, and tone of the original video.""",
            }
        ],
    )
    return response.content[0].text


async def _extract_key_topics(transcript: str) -> list[str]:
    """Use Claude to extract key topics from the transcript."""
    # Use first 5000 words if transcript is very long
    words = transcript.split()
    sample = " ".join(words[:5000]) if len(words) > 5000 else transcript

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Extract 5-10 key topics covered in this YouTube video transcript. Return ONLY a JSON array of strings, nothing else.

Example: ["compound interest", "index fund investing", "emergency funds"]

TRANSCRIPT:
{sample}""",
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Strip markdown if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


async def analyze_reference(youtube_url: str) -> dict:
    """Analyze a YouTube video and return structured reference context."""

    # Extract video ID
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return {"error": "Invalid YouTube URL. Please provide a valid YouTube video link."}

    # Get metadata
    try:
        metadata = _get_metadata(video_id)
    except Exception as e:
        return {"error": f"Could not access this video. It may be private, age-restricted, or unavailable. Details: {str(e)}"}

    # Get transcript
    transcript = _get_transcript(video_id)
    if not transcript:
        return {
            "error": "This video doesn't have captions/subtitles available. Try a different reference video that has auto-generated or manual captions enabled.",
            "title": metadata.get("title"),
        }

    # Check transcript length and summarize if needed
    word_count = len(transcript.split())
    transcript_for_context = transcript

    if word_count > 10000:
        try:
            transcript_for_context = await _summarize_transcript(transcript)
        except Exception:
            # If summarization fails, truncate instead
            transcript_for_context = " ".join(transcript.split()[:8000]) + "\n\n[Transcript truncated due to length]"

    # Extract key topics
    try:
        topics = await _extract_key_topics(transcript)
    except Exception:
        topics = []

    # Build reference context string
    topics_str = "\n".join(f"- {t}" for t in topics) if topics else "Could not extract topics"

    reference_context = f"""REFERENCE VIDEO ANALYSIS:
Title: {metadata['title']}
Channel: {metadata['channel']}
Duration: {metadata['duration']}
View Count: {metadata['view_count']:,}
Description: {metadata['description']}

TRANSCRIPT:
{transcript_for_context}

KEY TOPICS COVERED:
{topics_str}"""

    return {
        "title": metadata["title"],
        "duration": metadata["duration"],
        "duration_seconds": metadata["duration_seconds"],
        "view_count": metadata["view_count"],
        "channel": metadata["channel"],
        "topics": topics,
        "transcript_word_count": word_count,
        "reference_context": reference_context,
    }
