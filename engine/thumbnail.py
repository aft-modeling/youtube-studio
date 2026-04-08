import os
import uuid
import requests
import replicate
import anthropic
import json
import re
from PIL import Image, ImageDraw, ImageFont
from config import REPLICATE_API_TOKEN, ANTHROPIC_API_KEY

claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Visual style variations for the 3 thumbnails
STYLE_VARIANTS = [
    "vibrant colors, dramatic lighting, bold contrast, cinematic",
    "dark moody atmosphere, neon accents, high contrast, intense",
    "bright and clean, soft gradient background, professional, modern",
]


def _shorten_title(title: str, hook_text: str) -> str:
    """Use Claude to shorten the title to 3-5 impactful words for thumbnail."""
    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": f"""Shorten this YouTube video title to 3-5 punchy, impactful words for a thumbnail. Use power words. Make it attention-grabbing. Return ONLY the shortened text, nothing else.

Title: {title}
Hook: {hook_text}""",
                }
            ],
        )
        return response.content[0].text.strip().strip('"')
    except Exception:
        # Fallback: take first 5 words
        words = title.split()[:5]
        return " ".join(words)


def _generate_background(prompt: str, output_path: str) -> bool:
    """Generate a thumbnail background image using Replicate Flux."""
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    try:
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "jpg",
                "output_quality": 95,
            },
        )

        if hasattr(output, "url"):
            image_url = output.url
        elif isinstance(output, str):
            image_url = output
        else:
            image_url = str(output)

        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return True

    except Exception:
        return False


def _add_text_overlay(
    bg_path: str,
    output_path: str,
    text: str,
    variant_idx: int = 0,
) -> bool:
    """Add bold text overlay to a thumbnail background."""
    try:
        img = Image.open(bg_path).convert("RGB")
        img = img.resize((1280, 720), Image.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Try to load a bold font
        font = None
        font_size = 72
        for font_name in ["impact.ttf", "Impact.ttf", "arialbd.ttf", "Arial Bold.ttf", "calibrib.ttf"]:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except OSError:
                continue

        if font is None:
            font = ImageFont.load_default()

        # Split text into max 2 lines
        words = text.upper().split()
        if len(words) <= 3:
            lines = [" ".join(words)]
        else:
            mid = len(words) // 2
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]

        # Color schemes per variant
        color_schemes = [
            {"fill": (255, 255, 255), "stroke": (0, 0, 0)},      # White on black
            {"fill": (255, 215, 0), "stroke": (0, 0, 0)},         # Gold on black
            {"fill": (255, 255, 255), "stroke": (30, 30, 30)},     # White on dark
        ]
        scheme = color_schemes[variant_idx % len(color_schemes)]

        # Position: left-aligned with padding
        # Alternate left/right between variants
        x_offset = 60 if variant_idx % 2 == 0 else None  # None = calculate for right side

        # Calculate total text height
        line_heights = []
        line_widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        total_height = sum(line_heights) + (len(lines) - 1) * 10
        y_start = (720 - total_height) // 2

        for i, line in enumerate(lines):
            y = y_start + i * (line_heights[i] + 10)

            if x_offset is None:
                # Right-aligned
                x = 1280 - line_widths[i] - 60
            else:
                x = x_offset

            # Draw text stroke (outline) by drawing text offset in all directions
            stroke_width = 4
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx * dx + dy * dy <= stroke_width * stroke_width:
                        draw.text((x + dx, y + dy), line, fill=scheme["stroke"], font=font)

            # Draw main text
            draw.text((x, y), line, fill=scheme["fill"], font=font)

        img.save(output_path, "JPEG", quality=95)
        return True

    except Exception:
        return False


async def generate_thumbnails(
    title: str,
    topic: str,
    hook_text: str = "",
) -> dict:
    """Generate 2-3 thumbnail options for a video."""

    if not REPLICATE_API_TOKEN:
        return {"error": "Replicate API token not configured. Set REPLICATE_API_TOKEN in your .env file."}

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())[:8]

    # Shorten title for thumbnail text
    short_title = _shorten_title(title, hook_text or topic)

    thumbnail_paths = []

    for i, style in enumerate(STYLE_VARIANTS):
        bg_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumb_bg_{i}.jpg")
        final_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail_{i}.jpg")

        # Generate background
        prompt = f"YouTube thumbnail background, {topic}, {style}, 16:9 aspect ratio, eye-catching, no text, no words, no letters"

        if _generate_background(prompt, bg_path):
            # Add text overlay
            if _add_text_overlay(bg_path, final_path, short_title, variant_idx=i):
                thumbnail_paths.append(final_path)
            else:
                thumbnail_paths.append(bg_path)  # Use background without text as fallback

            # Clean up background file if final was created
            if os.path.exists(final_path) and os.path.exists(bg_path) and final_path != bg_path:
                try:
                    os.remove(bg_path)
                except OSError:
                    pass

    if not thumbnail_paths:
        return {"error": "Failed to generate any thumbnails. Check your Replicate API token."}

    return {
        "thumbnail_paths": thumbnail_paths,
        "short_title": short_title,
        "count": len(thumbnail_paths),
    }
