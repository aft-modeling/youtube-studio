import json
import re
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an elite YouTube scriptwriter who specializes in faceless educational and entertainment content. Your scripts consistently achieve 50%+ audience retention rates. You write in a conversational, engaging, slightly informal tone. You never sound like a textbook or a corporate presentation. You sound like a smart friend explaining something fascinating over coffee.

Your scripts follow a precise structure designed to maximize viewer retention:
1. HOOK (first 30 seconds / ~75 words): Open with a bold claim, surprising statistic, counterintuitive statement, or irresistible question that creates a curiosity gap. The viewer must feel compelled to keep watching. Never start with "In this video..." or "Today we're going to..."
2. CONTEXT (30 sec - 1.5 min / ~150 words): Briefly establish why this topic matters to the viewer personally. Create stakes. Make them feel like they NEED this information.
3. CORE CONTENT (main body / varies): Deliver the main value in 4-7 distinct sections. Each section needs:
   - A mini-hook or transition that re-engages attention
   - One clear point or insight
   - A concrete example, story, or data point
   - A "pattern interrupt" every 60-90 seconds (surprising fact, rhetorical question, hypothetical scenario, tonal shift)
4. CLIMAX (1-2 min before the end): The single most valuable, surprising, or mind-blowing insight. Reward viewers who stayed the whole time.
5. CTA + OUTRO (last 30 seconds / ~75 words): Brief, natural call to action. Don't beg for likes/subscribes — give them a reason. Suggest they'll enjoy another video on a related topic.

CRITICAL RULES:
- Use short sentences. Vary sentence length for rhythm.
- Use "you" and "your" constantly. Make it personal.
- Every 60-90 seconds of narration, include a pattern interrupt.
- Never use clichés like "buckle up", "dive in", "without further ado", "game-changer", or "let's get started."
- Write for SPOKEN delivery. Read it out loud in your head. If it sounds awkward spoken, rewrite it.
- Include [VISUAL: description] tags throughout the script. Place one after every 2-3 sentences. These describe what should be shown on screen (stock footage, graphics, text overlays, etc.)
- Include [TRANSITION] tags between major sections.

OUTPUT FORMAT:
Return ONLY valid JSON with this structure (no markdown, no backticks, no extra text):
{
  "title": "Compelling video title (with power words, numbers, or curiosity gaps)",
  "hook_text": "The opening hook as a standalone text (for thumbnail/title optimization)",
  "estimated_duration_minutes": <number>,
  "segments": [
    {
      "segment_number": 1,
      "segment_type": "hook | context | content | climax | cta",
      "segment_title": "Brief title for this segment",
      "narration": "The actual narration text for this segment...",
      "visual_cues": [
        "Description of what should be shown on screen during this segment",
        "Can have multiple visual cues per segment"
      ],
      "estimated_duration_seconds": <number>,
      "pattern_interrupt": "Optional: description of the pattern interrupt in this segment or null"
    }
  ],
  "tags": ["relevant", "youtube", "seo", "tags"],
  "description": "A YouTube description (2-3 sentences summarizing the video, with relevant keywords)"
}"""


def _build_user_prompt(
    topic: str,
    target_length_minutes: int,
    channel_niche: str,
    reference_context: str | None = None,
) -> str:
    target_word_count = target_length_minutes * 150

    prompt = f"""Write a YouTube script for a {channel_niche} channel.
Topic: {topic}
Target video length: {target_length_minutes} minutes (approximately {target_word_count} words of narration at 150 words per minute)"""

    if reference_context:
        prompt += f"""

Here is a reference for the style and topic coverage. DO NOT copy this. Use it only as inspiration for topic coverage and structure. Write a completely original script with different examples, different data points, and a fresh perspective:
---
{reference_context}
---"""

    return prompt


def _parse_json_response(text: str) -> dict:
    """Parse JSON from Claude's response, stripping markdown if needed."""
    cleaned = text.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

    return json.loads(cleaned)


def _validate_script(script: dict) -> bool:
    """Check that all required fields are present."""
    required_top = ["title", "hook_text", "estimated_duration_minutes", "segments", "tags", "description"]
    for field in required_top:
        if field not in script:
            return False

    if not isinstance(script["segments"], list) or len(script["segments"]) == 0:
        return False

    required_segment = ["segment_number", "segment_type", "segment_title", "narration", "visual_cues", "estimated_duration_seconds"]
    for seg in script["segments"]:
        for field in required_segment:
            if field not in seg:
                return False

    return True


def _count_narration_words(script: dict) -> int:
    """Count total narration words across all segments."""
    total = 0
    for seg in script["segments"]:
        total += len(seg["narration"].split())
    return total


async def generate_script(
    topic: str,
    target_length_minutes: int = 10,
    channel_niche: str = "general",
    reference_context: str | None = None,
) -> dict:
    """Generate a structured YouTube script using Claude."""

    user_prompt = _build_user_prompt(topic, target_length_minutes, channel_niche, reference_context)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError:
        return {"error": "Invalid Anthropic API key. Check your ANTHROPIC_API_KEY in the .env file."}
    except anthropic.APIError as e:
        return {"error": f"Claude API error: {str(e)}"}

    raw_text = response.content[0].text

    # Parse JSON
    try:
        script = _parse_json_response(raw_text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse script JSON from Claude's response.", "raw_response": raw_text[:500]}

    # Validate structure
    if not _validate_script(script):
        return {"error": "Script is missing required fields.", "raw_response": raw_text[:500]}

    # Check length — retry if more than 20% off target
    word_count = _count_narration_words(script)
    target_words = target_length_minutes * 150
    deviation = abs(word_count - target_words) / target_words

    if deviation > 0.2:
        direction = "longer" if word_count < target_words else "shorter"
        correction_prompt = f"""The script you just wrote has {word_count} words of narration, but the target is {target_words} words ({target_length_minutes} minutes at 150 words/minute).

Please rewrite the script to be {direction}. Target exactly {target_words} words of narration. Keep the same structure and quality, just adjust the length.

Return ONLY valid JSON in the same format as before (no markdown, no backticks)."""

        try:
            retry_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": raw_text},
                    {"role": "user", "content": correction_prompt},
                ],
            )

            retry_text = retry_response.content[0].text
            retry_script = _parse_json_response(retry_text)

            if _validate_script(retry_script):
                script = retry_script
                word_count = _count_narration_words(script)
        except Exception:
            # If retry fails, use the original script — it's still usable
            pass

    # Add metadata
    script["total_word_count"] = word_count
    script["estimated_duration_minutes"] = round(word_count / 150, 1)

    return script
