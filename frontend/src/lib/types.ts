export interface Channel {
  id: string;
  name: string;
  niche: string | null;
  elevenlabs_voice_id: string | null;
  voice_stability: number;
  voice_similarity: number;
  caption_font: string;
  caption_color: string;
  caption_highlight_color: string;
  caption_position: string;
  caption_font_size: number;
  default_video_length: string;
  intro_text: string | null;
  outro_text: string | null;
  music_genre: string;
  music_volume: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  project_count?: number;
}
