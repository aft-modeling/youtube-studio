import os
import uuid
import re

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Words that should stay attached to the next word
ARTICLES = {"a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their"}
PREPOSITIONS = {"in", "on", "at", "to", "for", "of", "with", "by", "from", "up", "about", "into", "over", "after", "under", "between", "through", "during", "before", "around", "among", "without"}
CONJUNCTIONS = {"and", "but", "or", "nor", "so", "yet"}
KEEP_WITH_NEXT = ARTICLES | PREPOSITIONS | CONJUNCTIONS


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert #RRGGBB hex to ASS &H00BBGGRR format."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "&H00FFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b}{g}{r}".upper()


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _group_words(word_timestamps: list[dict]) -> list[list[dict]]:
    """Group word timestamps into natural 2-4 word chunks."""
    if not word_timestamps:
        return []

    groups = []
    current_group = []

    for i, wt in enumerate(word_timestamps):
        word = wt["word"]
        clean_word = re.sub(r"[^\w']", "", word).lower()

        current_group.append(wt)

        # Decide whether to break after this word
        should_break = False

        # Break at punctuation (sentence/clause endings)
        if word.rstrip().endswith((",", ".", "!", "?", ";", ":", "—", "-")):
            should_break = True

        # Break if group has 3-4 words (unless current word leads into next)
        elif len(current_group) >= 3 and clean_word not in KEEP_WITH_NEXT:
            should_break = True

        # Force break at 4 words
        elif len(current_group) >= 4:
            should_break = True

        if should_break or i == len(word_timestamps) - 1:
            if current_group:
                groups.append(current_group)
                current_group = []

    return groups


def _build_ass_header(
    font_name: str = "Montserrat",
    font_size: int = 48,
    primary_color: str = "&H00FFFFFF",
    highlight_color: str = "&H0000D7FF",
    position: str = "bottom",
) -> str:
    """Build the ASS file header with styles."""

    # Alignment: 2 = bottom-center, 5 = center, 8 = top-center
    alignment_map = {"bottom": 2, "center": 5, "top": 8}
    alignment = alignment_map.get(position, 2)

    # MarginV adjusts vertical position
    margin_v_map = {"bottom": 60, "center": 0, "top": 60}
    margin_v = margin_v_map.get(position, 60)

    highlight_size = font_size + 4

    return f"""[Script Info]
Title: YouTube Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,{alignment},40,40,{margin_v},1
Style: Highlight,{font_name},{highlight_size},{highlight_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _generate_events(word_groups: list[list[dict]]) -> str:
    """Generate ASS dialogue events with word-by-word highlighting."""
    events = []

    for group in word_groups:
        if not group:
            continue

        group_start = group[0]["start"]
        group_end = group[-1]["end"]

        # For each word in the group, create an event where that word is highlighted
        for word_idx, current_word in enumerate(group):
            word_start = current_word["start"]
            word_end = current_word["end"]

            # Build the text line with highlighting
            parts = []
            for j, w in enumerate(group):
                clean = w["word"]
                if j == word_idx:
                    # This is the highlighted word
                    parts.append(f"{{\\rHighlight}}{clean}{{\\rDefault}}")
                else:
                    parts.append(clean)

            text = " ".join(parts)
            start_ts = _format_ass_time(word_start)
            end_ts = _format_ass_time(word_end)

            events.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
            )

    return "\n".join(events)


async def generate_captions(
    word_timestamps: list[dict],
    font_name: str = "Montserrat",
    font_size: int = 48,
    primary_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    position: str = "bottom",
) -> dict:
    """Generate an ASS subtitle file with word-by-word animated captions."""

    if not word_timestamps:
        return {"error": "No word timestamps provided."}

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())[:8]

    # Convert hex colors to ASS format
    ass_primary = _hex_to_ass_color(primary_color)
    ass_highlight = _hex_to_ass_color(highlight_color)

    # Group words into natural chunks
    word_groups = _group_words(word_timestamps)

    # Build ASS file
    header = _build_ass_header(
        font_name=font_name,
        font_size=font_size,
        primary_color=ass_primary,
        highlight_color=ass_highlight,
        position=position,
    )

    events = _generate_events(word_groups)

    ass_content = header + events + "\n"

    # Write ASS file
    ass_path = os.path.join(OUTPUT_DIR, f"{job_id}_captions.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return {
        "caption_file_path": ass_path,
        "total_groups": len(word_groups),
        "total_words": len(word_timestamps),
        "duration": word_timestamps[-1]["end"] if word_timestamps else 0,
    }
