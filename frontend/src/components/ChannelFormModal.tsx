"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import type { Channel } from "@/lib/types";

const NICHE_SUGGESTIONS = [
  "personal finance",
  "health & wellness",
  "technology",
  "true crime",
  "history",
  "science",
  "business",
  "real estate",
  "self improvement",
  "psychology",
];

const FONTS = [
  "Montserrat",
  "Bebas Neue",
  "Oswald",
  "Poppins",
  "Roboto Condensed",
];

const VIDEO_LENGTHS = ["8", "10", "12", "15", "20", "25", "30"];

const MUSIC_GENRES = ["ambient", "cinematic", "upbeat", "lo-fi", "dramatic"];

interface Props {
  channel: Channel | null;
  onClose: () => void;
  onSaved: () => void;
}

const defaults = {
  name: "",
  niche: "",
  elevenlabs_voice_id: "",
  voice_stability: 0.5,
  voice_similarity: 0.75,
  caption_font: "Montserrat",
  caption_color: "#FFFFFF",
  caption_highlight_color: "#FFD700",
  caption_position: "bottom",
  caption_font_size: 48,
  default_video_length: "10",
  intro_text: "",
  outro_text: "",
  music_genre: "ambient",
  music_volume: 0.15,
  notes: "",
};

export default function ChannelFormModal({ channel, onClose, onSaved }: Props) {
  const [form, setForm] = useState(defaults);
  const [saving, setSaving] = useState(false);
  const [showNicheSuggestions, setShowNicheSuggestions] = useState(false);

  useEffect(() => {
    if (channel) {
      setForm({
        name: channel.name,
        niche: channel.niche || "",
        elevenlabs_voice_id: channel.elevenlabs_voice_id || "",
        voice_stability: channel.voice_stability,
        voice_similarity: channel.voice_similarity,
        caption_font: channel.caption_font,
        caption_color: channel.caption_color,
        caption_highlight_color: channel.caption_highlight_color,
        caption_position: channel.caption_position,
        caption_font_size: channel.caption_font_size,
        default_video_length: channel.default_video_length,
        intro_text: channel.intro_text || "",
        outro_text: channel.outro_text || "",
        music_genre: channel.music_genre,
        music_volume: channel.music_volume,
        notes: channel.notes || "",
      });
    }
  }, [channel]);

  const set = (key: string, value: string | number) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);

    const payload = {
      ...form,
      niche: form.niche || null,
      elevenlabs_voice_id: form.elevenlabs_voice_id || null,
      intro_text: form.intro_text || null,
      outro_text: form.outro_text || null,
      notes: form.notes || null,
    };

    const url = channel ? `/api/channels/${channel.id}` : "/api/channels";
    const method = channel ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setSaving(false);

    if (res.ok) {
      onSaved();
    }
  }

  const filteredNiches = NICHE_SUGGESTIONS.filter((n) =>
    n.toLowerCase().includes(form.niche.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm overflow-y-auto py-8">
      <div className="bg-card border border-border rounded-2xl w-full max-w-2xl mx-4 shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-bold text-white">
            {channel ? "Edit Channel" : "New Channel"}
          </h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Channel Name *
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent"
                placeholder="My Awesome Channel"
              />
            </div>

            <div className="relative">
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Niche
              </label>
              <input
                type="text"
                value={form.niche}
                onChange={(e) => set("niche", e.target.value)}
                onFocus={() => setShowNicheSuggestions(true)}
                onBlur={() =>
                  setTimeout(() => setShowNicheSuggestions(false), 150)
                }
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent"
                placeholder="e.g., personal finance"
              />
              {showNicheSuggestions && filteredNiches.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-xl max-h-48 overflow-y-auto">
                  {filteredNiches.map((n) => (
                    <button
                      key={n}
                      type="button"
                      className="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-card-hover"
                      onClick={() => {
                        set("niche", n);
                        setShowNicheSuggestions(false);
                      }}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Voice Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-accent uppercase tracking-wider">
              Voice Settings
            </h3>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                ElevenLabs Voice ID
              </label>
              <input
                type="text"
                value={form.elevenlabs_voice_id}
                onChange={(e) => set("elevenlabs_voice_id", e.target.value)}
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm font-mono focus:outline-none focus:border-accent"
                placeholder="Paste your voice ID here"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Stability: {form.voice_stability.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={form.voice_stability}
                  onChange={(e) =>
                    set("voice_stability", parseFloat(e.target.value))
                  }
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Similarity: {form.voice_similarity.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={form.voice_similarity}
                  onChange={(e) =>
                    set("voice_similarity", parseFloat(e.target.value))
                  }
                  className="w-full"
                />
              </div>
            </div>
          </div>

          {/* Caption Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-accent uppercase tracking-wider">
              Caption Style
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Font
                </label>
                <select
                  value={form.caption_font}
                  onChange={(e) => set("caption_font", e.target.value)}
                  className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent"
                >
                  {FONTS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Font Size: {form.caption_font_size}px
                </label>
                <input
                  type="range"
                  min="32"
                  max="72"
                  step="2"
                  value={form.caption_font_size}
                  onChange={(e) =>
                    set("caption_font_size", parseInt(e.target.value))
                  }
                  className="w-full"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Primary Color
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={form.caption_color}
                    onChange={(e) => set("caption_color", e.target.value)}
                    className="w-10 h-10 rounded border border-border cursor-pointer bg-transparent"
                  />
                  <span className="text-xs text-muted font-mono">
                    {form.caption_color}
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Highlight Color
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={form.caption_highlight_color}
                    onChange={(e) =>
                      set("caption_highlight_color", e.target.value)
                    }
                    className="w-10 h-10 rounded border border-border cursor-pointer bg-transparent"
                  />
                  <span className="text-xs text-muted font-mono">
                    {form.caption_highlight_color}
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Position
                </label>
                <div className="flex gap-1">
                  {["bottom", "center", "top"].map((pos) => (
                    <button
                      key={pos}
                      type="button"
                      onClick={() => set("caption_position", pos)}
                      className={`flex-1 px-2 py-2 text-xs rounded-lg border transition-colors ${
                        form.caption_position === pos
                          ? "bg-accent text-white border-accent"
                          : "bg-input-bg text-muted border-border hover:text-white"
                      }`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Video & Music Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-accent uppercase tracking-wider">
              Video & Music
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Default Video Length
                </label>
                <select
                  value={form.default_video_length}
                  onChange={(e) => set("default_video_length", e.target.value)}
                  className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent"
                >
                  {VIDEO_LENGTHS.map((l) => (
                    <option key={l} value={l}>
                      {l} minutes
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Music Genre
                </label>
                <select
                  value={form.music_genre}
                  onChange={(e) => set("music_genre", e.target.value)}
                  className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent"
                >
                  {MUSIC_GENRES.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Music Volume: {form.music_volume.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="0.5"
                step="0.05"
                value={form.music_volume}
                onChange={(e) =>
                  set("music_volume", parseFloat(e.target.value))
                }
                className="w-full"
              />
            </div>
          </div>

          {/* Text Fields */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-accent uppercase tracking-wider">
              Intro / Outro
            </h3>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Intro Text
              </label>
              <textarea
                value={form.intro_text}
                onChange={(e) => set("intro_text", e.target.value)}
                rows={2}
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent resize-none"
                placeholder="Optional intro text overlay"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Outro Text / CTA
              </label>
              <textarea
                value={form.outro_text}
                onChange={(e) => set("outro_text", e.target.value)}
                rows={2}
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent resize-none"
                placeholder="Optional outro/CTA text"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Notes
              </label>
              <textarea
                value={form.notes}
                onChange={(e) => set("notes", e.target.value)}
                rows={3}
                className="w-full px-3 py-2.5 bg-input-bg border border-border rounded-lg text-white text-sm focus:outline-none focus:border-accent resize-none"
                placeholder="Free-form notes about this channel"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm text-muted hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.name.trim()}
              className="px-6 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving
                ? "Saving..."
                : channel
                  ? "Save Changes"
                  : "Create Channel"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
