import os
import uuid
import subprocess
import random
from pydub import AudioSegment

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")


def _ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def _run_ffmpeg(cmd: list[str], timeout: int = 600) -> bool:
    """Run an FFmpeg command. Returns True on success."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _get_duration(file_path: str) -> float:
    """Get the duration of a media file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        import json
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0


# ─── Stage 1: Prepare individual visual clips ───────────────────────────

def _prepare_video_clip(input_path: str, output_path: str, duration: float) -> bool:
    """Trim, resize, and remove audio from a video clip."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        "-an",  # remove audio
        "-c:v", "libx264",
        "-preset", "fast",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    return _run_ffmpeg(cmd)


def _prepare_image_clip(input_path: str, output_path: str, duration: float, ken_burns: bool = True) -> bool:
    """Create a video clip from a still image, optionally with Ken Burns effect."""
    total_frames = int(duration * 30)

    if ken_burns and total_frames > 1:
        # Random Ken Burns direction
        effect = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])

        if effect == "zoom_in":
            vf = f"zoompan=z='min(zoom+0.0005,1.1)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
        elif effect == "zoom_out":
            vf = f"zoompan=z='if(eq(on,1),1.1,max(zoom-0.0005,1.0))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
        elif effect == "pan_right":
            vf = f"zoompan=z=1.1:d={total_frames}:x='if(eq(on,1),0,min(x+2,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
        else:  # pan_left
            vf = f"zoompan=z=1.1:d={total_frames}:x='if(eq(on,1),iw,max(x-2,0))':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"
    else:
        vf = f"zoompan=z=1:d={total_frames}:s=1920x1080:fps=30"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", input_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    return _run_ffmpeg(cmd)


def _create_title_card(text: str, output_path: str, duration: float = 3.0) -> bool:
    """Create a title/outro card with text on dark background."""
    # Escape special characters for FFmpeg drawtext
    escaped = text.replace("'", "'\\''").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x0f1117:s=1920x1080:d={duration}:r=30",
        "-vf", (
            f"drawtext=text='{escaped}'"
            f":fontsize=64:fontcolor=white"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
            f":font=Arial"
            f",fade=in:st=0:d=0.5,fade=out:st={duration-0.5}:d=0.5"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    return _run_ffmpeg(cmd)


# ─── Stage 2: Concatenate clips ─────────────────────────────────────────

def _concatenate_clips(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate video clips using FFmpeg concat demuxer with crossfade."""
    if not clip_paths:
        return False

    if len(clip_paths) == 1:
        # Just copy the single clip
        cmd = ["ffmpeg", "-y", "-i", clip_paths[0], "-c", "copy", output_path]
        return _run_ffmpeg(cmd)

    # For multiple clips, use concat with xfade filter
    # Build filter graph for crossfade transitions
    fade_duration = 0.3  # Short crossfade

    # Start with simple concat for reliability
    concat_file = output_path + ".txt"
    with open(concat_file, "w") as f:
        for path in clip_paths:
            # Use forward slashes for FFmpeg compatibility
            clean_path = path.replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        output_path,
    ]
    success = _run_ffmpeg(cmd)

    # Clean up concat file
    try:
        os.remove(concat_file)
    except OSError:
        pass

    return success


# ─── Stage 3: Mix audio ─────────────────────────────────────────────────

def _mix_audio(
    voiceover_path: str,
    music_path: str | None,
    output_path: str,
    music_volume: float = 0.15,
    total_duration: float = 0,
) -> bool:
    """Mix voiceover with background music at specified volume."""
    if not music_path or not os.path.exists(music_path):
        # No music — just use voiceover as-is
        cmd = ["ffmpeg", "-y", "-i", voiceover_path, "-c:a", "aac", "-b:a", "192k", output_path]
        return _run_ffmpeg(cmd)

    # Get voiceover duration
    vo_duration = _get_duration(voiceover_path)
    if vo_duration <= 0:
        vo_duration = total_duration or 60

    # Loop music if needed, apply volume, mix with voiceover
    cmd = [
        "ffmpeg", "-y",
        "-i", voiceover_path,
        "-stream_loop", "-1",
        "-i", music_path,
        "-filter_complex", (
            f"[1:a]volume={music_volume},atrim=0:{vo_duration},apad[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[out]"
        ),
        "-map", "[out]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(vo_duration),
        output_path,
    ]
    return _run_ffmpeg(cmd)


# ─── Stage 4: Final assembly ────────────────────────────────────────────

async def assemble_video(
    project_id: str,
    voiceover_path: str,
    visual_timeline: list[dict],
    caption_path: str | None = None,
    music_path: str | None = None,
    music_volume: float = 0.15,
    intro_text: str | None = None,
    outro_text: str | None = None,
) -> dict:
    """Assemble all components into a final MP4 video."""

    _ensure_dirs()
    job_id = project_id or str(uuid.uuid4())[:8]
    job_temp = os.path.join(TEMP_DIR, f"assembly_{job_id}")
    os.makedirs(job_temp, exist_ok=True)

    # Validate inputs
    if not os.path.exists(voiceover_path):
        return {"error": f"Voiceover file not found: {voiceover_path}"}

    if not visual_timeline:
        return {"error": "No visual timeline provided."}

    # ── Step 1: Prepare each visual clip ──
    prepared_clips = []
    clip_idx = 0

    # Optional intro card
    if intro_text:
        intro_path = os.path.join(job_temp, "intro.mp4")
        if _create_title_card(intro_text, intro_path, duration=3.0):
            prepared_clips.append(intro_path)

    for item in visual_timeline:
        asset_path = item.get("asset_path")
        asset_type = item.get("asset_type", "image")
        duration = item.get("duration", 10)
        ken_burns = item.get("ken_burns", False)

        if not asset_path or not os.path.exists(asset_path):
            # Create a dark placeholder clip
            placeholder_path = os.path.join(job_temp, f"placeholder_{clip_idx}.mp4")
            _create_title_card("", placeholder_path, duration=duration)
            prepared_clips.append(placeholder_path)
            clip_idx += 1
            continue

        clip_path = os.path.join(job_temp, f"clip_{clip_idx}.mp4")

        if asset_type == "stock_video":
            success = _prepare_video_clip(asset_path, clip_path, duration)
        else:
            # image, ai_image, text_overlay — all treated as still images
            success = _prepare_image_clip(asset_path, clip_path, duration, ken_burns=ken_burns)

        if success:
            prepared_clips.append(clip_path)
        else:
            # Fallback: dark placeholder
            placeholder_path = os.path.join(job_temp, f"placeholder_{clip_idx}.mp4")
            _create_title_card("", placeholder_path, duration=duration)
            prepared_clips.append(placeholder_path)

        clip_idx += 1

    # Optional outro card
    if outro_text:
        outro_path = os.path.join(job_temp, "outro.mp4")
        if _create_title_card(outro_text, outro_path, duration=5.0):
            prepared_clips.append(outro_path)

    if not prepared_clips:
        return {"error": "No visual clips could be prepared."}

    # ── Step 2: Concatenate all visual clips ──
    visual_track = os.path.join(job_temp, "visual_track.mp4")
    if not _concatenate_clips(prepared_clips, visual_track):
        return {"error": "Failed to concatenate visual clips."}

    # ── Step 3: Mix audio (voiceover + background music) ──
    vo_duration = _get_duration(voiceover_path)
    mixed_audio = os.path.join(job_temp, "mixed_audio.aac")
    _mix_audio(voiceover_path, music_path, mixed_audio, music_volume, vo_duration)

    # ── Step 4: Combine video + audio + captions ──
    final_output = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")

    # Build the FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", visual_track,
        "-i", mixed_audio,
    ]

    # Build video filter for captions
    vf_filters = []

    if caption_path and os.path.exists(caption_path):
        # Escape path for ASS filter (use forward slashes, escape colons)
        ass_path = caption_path.replace("\\", "/").replace(":", "\\:")
        vf_filters.append(f"ass='{ass_path}'")

    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])

    cmd.extend([
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", "8M",
        "-maxrate", "10M",
        "-bufsize", "16M",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        final_output,
    ])

    if not _run_ffmpeg(cmd, timeout=600):
        return {"error": "Final video render failed."}

    # Get final duration
    final_duration = _get_duration(final_output)

    # Clean up temp files
    import shutil
    try:
        shutil.rmtree(job_temp)
    except OSError:
        pass

    return {
        "video_path": final_output,
        "duration_seconds": round(final_duration, 2),
    }
