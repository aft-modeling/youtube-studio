import os
import json
import re
import uuid
import requests
import replicate
import anthropic
from PIL import Image, ImageDraw, ImageFont
from config import PEXELS_API_KEY, REPLICATE_API_TOKEN, ANTHROPIC_API_KEY

claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

VISUALS_DIR = os.path.join(os.path.dirname(__file__), "temp", "visuals")
FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")


def _ensure_dirs():
    os.makedirs(VISUALS_DIR, exist_ok=True)


# ─── 1. Visual Cue Classifier ───────────────────────────────────────────

async def _classify_visual_cues(visual_cues: list[str]) -> list[dict]:
    """Use Claude to classify each visual cue and generate search queries."""
    cues_text = "\n".join(f"{i+1}. {cue}" for i, cue in enumerate(visual_cues))

    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": f"""Classify each visual cue for a YouTube video into one of these categories:
- "stock_video": concrete, filmable scenes (people, places, nature, objects in motion)
- "stock_image": concrete but static subjects (objects, places, portraits)
- "ai_image": abstract concepts, metaphors, or very specific scenes unlikely to exist as stock
- "text_overlay": statistics, numbers, text displays, quotes

For stock_video and stock_image, also provide a short, specific Pexels search query (2-4 words).
For ai_image, provide an image generation prompt.
For text_overlay, provide the text to display.

Return ONLY valid JSON array, no markdown:
[
  {{"cue": "original cue", "type": "stock_video", "search_query": "city skyline night"}},
  {{"cue": "original cue", "type": "ai_image", "prompt": "detailed prompt for image generation"}},
  {{"cue": "original cue", "type": "text_overlay", "display_text": "90% of people fail"}}
]

VISUAL CUES:
{cues_text}""",
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: treat all as stock_image
        return [{"cue": cue, "type": "stock_image", "search_query": cue[:50]} for cue in visual_cues]


# ─── 2. Pexels Search + Download ────────────────────────────────────────

def _search_pexels_videos(query: str, min_duration: int = 5) -> dict | None:
    """Search Pexels for landscape video clips."""
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 15, "orientation": "landscape"}

    resp = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params)
    if resp.status_code != 200:
        return None

    data = resp.json()
    for video in data.get("video_files", []) if "video_files" in data else []:
        pass  # handled below

    # Find best video from results
    for result in data.get("videos", []):
        # Filter: landscape and decent duration
        if result.get("width", 0) < result.get("height", 0):
            continue  # skip portrait

        # Find best quality video file (prefer HD)
        best_file = None
        for vf in result.get("video_files", []):
            w = vf.get("width", 0)
            h = vf.get("height", 0)
            if w < h:
                continue  # skip portrait files
            if w >= 1280:
                if best_file is None or w > best_file.get("width", 0):
                    best_file = vf

        if best_file and best_file.get("link"):
            return {
                "url": best_file["link"],
                "width": best_file.get("width", 1920),
                "height": best_file.get("height", 1080),
                "duration": result.get("duration", 10),
                "source": "pexels",
            }

    return None


def _search_pexels_images(query: str) -> dict | None:
    """Search Pexels for landscape images."""
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "landscape", "size": "large"}

    resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
    if resp.status_code != 200:
        return None

    data = resp.json()
    for photo in data.get("photos", []):
        src = photo.get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("original")
        if url and photo.get("width", 0) >= photo.get("height", 0):
            return {
                "url": url,
                "width": photo.get("width", 1920),
                "height": photo.get("height", 1080),
                "source": "pexels",
            }

    return None


def _download_file(url: str, output_path: str) -> bool:
    """Download a file from URL to local path."""
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception:
        return False


# ─── 3. Replicate/Flux Image Generation ─────────────────────────────────

def _generate_ai_image(prompt: str, output_path: str) -> bool:
    """Generate an image using Replicate Flux model."""
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    enhanced_prompt = f"{prompt}, photorealistic, 16:9 aspect ratio, high quality, cinematic lighting, YouTube video screenshot style"

    try:
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": enhanced_prompt,
                "aspect_ratio": "16:9",
                "output_format": "jpg",
                "output_quality": 90,
            },
        )

        # Output can be a URL string or a FileOutput object
        if hasattr(output, "url"):
            image_url = output.url
        elif isinstance(output, str):
            image_url = output
        else:
            image_url = str(output)

        return _download_file(image_url, output_path)

    except Exception:
        return False


# ─── 4. Pillow Text Overlay Generator ───────────────────────────────────

def _create_text_overlay(text: str, output_path: str) -> bool:
    """Create a 1920x1080 dark background image with centered text."""
    try:
        img = Image.new("RGB", (1920, 1080), color=(15, 17, 23))
        draw = ImageDraw.Draw(img)

        # Try to load a nice font, fall back to default
        font_large = None
        font_small = None
        try:
            # Try common system fonts
            for font_name in ["arial.ttf", "Arial.ttf", "calibri.ttf", "segoeui.ttf"]:
                try:
                    font_large = ImageFont.truetype(font_name, 72)
                    font_small = ImageFont.truetype(font_name, 36)
                    break
                except OSError:
                    continue
        except Exception:
            pass

        if font_large is None:
            font_large = ImageFont.load_default()
            font_small = font_large

        # Split text into main stat and context
        lines = text.split("\n") if "\n" in text else [text]

        if len(lines) >= 2:
            main_text = lines[0]
            sub_text = "\n".join(lines[1:])
        else:
            main_text = text
            sub_text = None

        # Draw main text centered
        bbox = draw.textbbox((0, 0), main_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (1920 - text_width) // 2
        y = (1080 - text_height) // 2 - (30 if sub_text else 0)

        # Draw text shadow
        draw.text((x + 3, y + 3), main_text, fill=(0, 0, 0), font=font_large)
        draw.text((x, y), main_text, fill=(255, 255, 255), font=font_large)

        # Draw subtitle if present
        if sub_text:
            bbox_sub = draw.textbbox((0, 0), sub_text, font=font_small)
            sub_width = bbox_sub[2] - bbox_sub[0]
            sx = (1920 - sub_width) // 2
            sy = y + text_height + 30
            draw.text((sx, sy), sub_text, fill=(180, 180, 180), font=font_small)

        img.save(output_path, "JPEG", quality=95)
        return True

    except Exception:
        return False


# ─── 5. Main Pipeline ───────────────────────────────────────────────────

async def generate_visuals(script_segments: list[dict], project_id: str = "") -> dict:
    """Generate visual assets for all script segments."""

    if not PEXELS_API_KEY:
        return {"error": "Pexels API key not configured. Set PEXELS_API_KEY in your .env file."}

    _ensure_dirs()
    job_id = project_id or str(uuid.uuid4())[:8]
    job_dir = os.path.join(VISUALS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Collect all visual cues from segments
    all_cues = []
    cue_to_segment = []  # track which segment each cue belongs to
    for seg in script_segments:
        for cue in seg.get("visual_cues", []):
            all_cues.append(cue)
            cue_to_segment.append(seg)

    if not all_cues:
        return {"error": "No visual cues found in script segments."}

    # Classify all cues at once
    classifications = await _classify_visual_cues(all_cues)

    # Process each visual cue
    visual_timeline = []
    cumulative_time = 0.0

    for seg_idx, seg in enumerate(script_segments):
        seg_duration = seg.get("estimated_duration_seconds", 15)
        seg_cues = seg.get("visual_cues", [])
        if not seg_cues:
            cumulative_time += seg_duration
            continue

        # Divide segment time evenly among its visual cues
        cue_duration = seg_duration / len(seg_cues)

        for cue_idx, cue in enumerate(seg_cues):
            start_time = cumulative_time + (cue_idx * cue_duration)
            end_time = start_time + cue_duration

            # Find classification for this cue
            classification = None
            for c in classifications:
                if c.get("cue", "") == cue:
                    classification = c
                    break

            if classification is None:
                classification = {"cue": cue, "type": "stock_image", "search_query": cue[:50]}

            asset_type = classification.get("type", "stock_image")
            asset_path = None
            search_query = ""
            source = ""

            if asset_type == "text_overlay":
                display_text = classification.get("display_text", cue)
                filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_text.jpg"
                asset_path = os.path.join(job_dir, filename)
                success = _create_text_overlay(display_text, asset_path)
                source = "generated"
                search_query = display_text

            elif asset_type == "ai_image":
                prompt = classification.get("prompt", cue)
                filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_ai.jpg"
                asset_path = os.path.join(job_dir, filename)
                success = _generate_ai_image(prompt, asset_path)
                source = "replicate"
                search_query = prompt

                if not success:
                    # Fall back to Pexels image search
                    fallback_query = " ".join(cue.split()[:4])
                    result = _search_pexels_images(fallback_query)
                    if result:
                        filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_fallback.jpg"
                        asset_path = os.path.join(job_dir, filename)
                        success = _download_file(result["url"], asset_path)
                        source = "pexels"
                        search_query = fallback_query
                        asset_type = "stock_image"

            elif asset_type == "stock_video":
                search_query = classification.get("search_query", cue[:50])
                result = _search_pexels_videos(search_query)
                if result:
                    filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_video.mp4"
                    asset_path = os.path.join(job_dir, filename)
                    success = _download_file(result["url"], asset_path)
                    source = "pexels"
                else:
                    # Fall back to stock image
                    result = _search_pexels_images(search_query)
                    if result:
                        filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_img.jpg"
                        asset_path = os.path.join(job_dir, filename)
                        success = _download_file(result["url"], asset_path)
                        source = "pexels"
                        asset_type = "stock_image"
                    else:
                        # Fall back to AI generation
                        filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_ai.jpg"
                        asset_path = os.path.join(job_dir, filename)
                        success = _generate_ai_image(cue, asset_path)
                        source = "replicate"
                        asset_type = "ai_image"

            else:  # stock_image
                search_query = classification.get("search_query", cue[:50])
                result = _search_pexels_images(search_query)
                if result:
                    filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_img.jpg"
                    asset_path = os.path.join(job_dir, filename)
                    success = _download_file(result["url"], asset_path)
                    source = "pexels"
                else:
                    # Fall back to AI generation
                    filename = f"{job_id}_seg{seg_idx}_cue{cue_idx}_ai.jpg"
                    asset_path = os.path.join(job_dir, filename)
                    success = _generate_ai_image(cue, asset_path)
                    source = "replicate"
                    asset_type = "ai_image"

            visual_timeline.append({
                "segment_number": seg.get("segment_number", seg_idx + 1),
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "asset_type": asset_type,
                "asset_path": asset_path if asset_path and os.path.exists(asset_path) else None,
                "search_query": search_query,
                "source": source,
                "ken_burns": asset_type in ("stock_image", "ai_image"),
                "duration": round(cue_duration, 2),
            })

        cumulative_time += seg_duration

    return {
        "visual_timeline": visual_timeline,
        "total_assets": len(visual_timeline),
        "assets_dir": job_dir,
    }
