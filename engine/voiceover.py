import os
import re
import base64
import uuid
import numpy as np
from pydub import AudioSegment
import noisereduce as nr
from elevenlabs import ElevenLabs
from elevenlabs.types import VoiceSettings
from config import ELEVENLABS_API_KEY

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
CHUNK_CHAR_LIMIT = 4500  # Stay under ElevenLabs per-request limit


def _ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def _split_into_chunks(text: str, limit: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """Split text at sentence boundaries into chunks under the character limit."""
    if len(text) <= limit:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > limit:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = (current_chunk + " " + sentence).strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _generate_chunk_audio(
    text: str,
    voice_id: str,
    stability: float,
    similarity: float,
    previous_text: str | None = None,
    next_text: str | None = None,
) -> tuple[bytes, list[dict]]:
    """Generate audio for a single text chunk. Returns (audio_bytes, word_timestamps)."""
    response = client.text_to_speech.convert_with_timestamps(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_192",
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity,
        ),
        previous_text=previous_text,
        next_text=next_text,
    )

    # Response contains audio_base64 and alignment
    audio_base64 = response.get("audio_base64", "")
    alignment = response.get("alignment", {})

    audio_bytes = base64.b64decode(audio_base64) if audio_base64 else b""

    # Extract word timestamps from alignment
    word_timestamps = []
    if alignment:
        characters = alignment.get("characters", [])
        char_start_times = alignment.get("character_start_times_seconds", [])
        char_end_times = alignment.get("character_end_times_seconds", [])

        if characters and char_start_times and char_end_times:
            # Group characters into words
            current_word = ""
            word_start = None

            for i, char in enumerate(characters):
                if char == " " or i == len(characters) - 1:
                    if i == len(characters) - 1 and char != " ":
                        current_word += char

                    if current_word.strip():
                        word_timestamps.append({
                            "word": current_word.strip(),
                            "start": word_start,
                            "end": char_end_times[i] if i == len(characters) - 1 else char_end_times[i - 1],
                        })
                    current_word = ""
                    word_start = None
                else:
                    if word_start is None:
                        word_start = char_start_times[i]
                    current_word += char

    return audio_bytes, word_timestamps


def _enhance_audio(audio: AudioSegment) -> AudioSegment:
    """Enhance audio: normalize, noise reduce, compress, high-pass filter."""

    # 1. Normalize to -3dB
    change_in_dbfs = -3.0 - audio.dBFS
    audio = audio.apply_gain(change_in_dbfs)

    # 2. Noise reduction
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    sample_rate = audio.frame_rate

    # Apply noise reduction
    reduced = nr.reduce_noise(
        y=samples,
        sr=sample_rate,
        prop_decrease=0.6,
        stationary=True,
    )

    # Convert back to AudioSegment
    reduced_int = np.int16(np.clip(reduced, -32768, 32767))
    audio = AudioSegment(
        reduced_int.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=audio.channels,
    )

    # 3. High-pass filter at 80Hz to remove rumble
    audio = audio.high_pass_filter(80)

    # 4. Gentle compression — reduce peaks above -10dB
    # Simple approach: reduce gain on loud segments
    threshold_db = -10.0
    if audio.max_dBFS > threshold_db:
        excess = audio.max_dBFS - threshold_db
        audio = audio.apply_gain(-excess * 0.5)

    # Re-normalize to -3dB after processing
    change_in_dbfs = -3.0 - audio.dBFS
    audio = audio.apply_gain(change_in_dbfs)

    return audio


async def generate_voiceover(
    script_text: str,
    voice_id: str,
    stability: float = 0.5,
    similarity: float = 0.75,
) -> dict:
    """Generate voiceover audio with word-level timestamps."""

    if not ELEVENLABS_API_KEY:
        return {"error": "ElevenLabs API key not configured. Set ELEVENLABS_API_KEY in your .env file."}

    if not voice_id:
        return {"error": "No voice ID provided. Set an ElevenLabs voice ID in your channel settings."}

    _ensure_dirs()
    job_id = str(uuid.uuid4())[:8]

    # Split text into chunks if needed
    chunks = _split_into_chunks(script_text)

    all_audio_bytes = []
    all_timestamps = []
    cumulative_duration = 0.0

    try:
        for i, chunk in enumerate(chunks):
            prev_text = chunks[i - 1][-200:] if i > 0 else None
            next_text = chunks[i + 1][:200] if i < len(chunks) - 1 else None

            audio_bytes, timestamps = _generate_chunk_audio(
                text=chunk,
                voice_id=voice_id,
                stability=stability,
                similarity=similarity,
                previous_text=prev_text,
                next_text=next_text,
            )

            if not audio_bytes:
                return {"error": f"ElevenLabs returned empty audio for chunk {i + 1}/{len(chunks)}."}

            # Save temp chunk file
            chunk_path = os.path.join(TEMP_DIR, f"{job_id}_chunk_{i}.mp3")
            with open(chunk_path, "wb") as f:
                f.write(audio_bytes)

            all_audio_bytes.append(chunk_path)

            # Offset timestamps by cumulative duration
            for ts in timestamps:
                all_timestamps.append({
                    "word": ts["word"],
                    "start": round(ts["start"] + cumulative_duration, 3),
                    "end": round(ts["end"] + cumulative_duration, 3),
                })

            # Get chunk duration for offset calculation
            chunk_audio = AudioSegment.from_mp3(chunk_path)
            cumulative_duration += chunk_audio.duration_seconds

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return {"error": "Invalid ElevenLabs API key. Check your ELEVENLABS_API_KEY."}
        return {"error": f"ElevenLabs API error: {error_msg}"}

    # Concatenate all chunks
    combined = AudioSegment.empty()
    for chunk_path in all_audio_bytes:
        combined += AudioSegment.from_mp3(chunk_path)

    # Enhance audio
    enhanced = _enhance_audio(combined)

    # Export files
    mp3_path = os.path.join(OUTPUT_DIR, f"{job_id}_voiceover.mp3")
    wav_path = os.path.join(OUTPUT_DIR, f"{job_id}_voiceover.wav")

    enhanced.export(mp3_path, format="mp3", bitrate="192k")
    enhanced.export(wav_path, format="wav")

    # Clean up temp files
    for chunk_path in all_audio_bytes:
        try:
            os.remove(chunk_path)
        except OSError:
            pass

    duration_seconds = round(enhanced.duration_seconds, 2)

    return {
        "audio_file_path": mp3_path,
        "wav_file_path": wav_path,
        "word_timestamps": all_timestamps,
        "duration_seconds": duration_seconds,
        "chunks_processed": len(chunks),
    }
