"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Pencil, Trash2, Tv } from "lucide-react";
import { toast } from "sonner";
import type { Channel } from "@/lib/types";
import ChannelFormModal from "@/components/ChannelFormModal";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchChannels = useCallback(async () => {
    const res = await fetch("/api/channels");
    if (res.ok) {
      setChannels(await res.json());
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

  function openNew() {
    setEditingChannel(null);
    setShowForm(true);
  }

  function openEdit(channel: Channel) {
    setEditingChannel(channel);
    setShowForm(true);
  }

  async function handleDelete(id: string) {
    const res = await fetch(`/api/channels/${id}`, { method: "DELETE" });
    if (res.ok) {
      toast.success("Channel deleted");
      setDeleteConfirm(null);
      fetchChannels();
    } else {
      toast.error("Failed to delete channel");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditingChannel(null);
    toast.success(editingChannel ? "Channel updated" : "Channel created");
    fetchChannels();
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-muted">Loading channels...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Channels</h1>
          <p className="text-muted text-sm mt-1">
            Manage your YouTube channel configurations
          </p>
        </div>
        <button
          onClick={openNew}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Channel
        </button>
      </div>

      {channels.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center">
          <Tv className="w-12 h-12 text-muted mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-white mb-2">
            No channels yet
          </h2>
          <p className="text-muted text-sm mb-6">
            Create your first channel to get started making videos.
          </p>
          <button
            onClick={openNew}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Channel
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {channels.map((channel) => (
            <div
              key={channel.id}
              className="bg-card border border-border rounded-xl p-5 hover:border-border hover:bg-card-hover transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-semibold truncate">
                    {channel.name}
                  </h3>
                  {channel.niche && (
                    <span className="inline-block mt-1 px-2 py-0.5 bg-accent/10 text-accent text-xs rounded-full">
                      {channel.niche}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(channel)}
                    className="p-1.5 text-muted hover:text-white rounded-lg hover:bg-background transition-colors"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(channel.id)}
                    className="p-1.5 text-muted hover:text-danger rounded-lg hover:bg-background transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                {channel.elevenlabs_voice_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-muted">Voice ID</span>
                    <span className="text-foreground font-mono text-xs truncate max-w-[140px]">
                      {channel.elevenlabs_voice_id}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-muted">Caption Style</span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded-full border border-border"
                      style={{ backgroundColor: channel.caption_highlight_color }}
                    />
                    <span className="text-foreground text-xs">
                      {channel.caption_font} · {channel.caption_font_size}px
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Videos</span>
                  <span className="text-foreground">
                    {channel.project_count || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Created</span>
                  <span className="text-foreground text-xs">
                    {new Date(channel.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl p-6 max-w-sm mx-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">
              Delete Channel?
            </h3>
            <p className="text-muted text-sm mb-6">
              This will permanently delete this channel and all its associated
              video projects. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm text-muted hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 bg-danger hover:bg-danger-hover text-white text-sm font-medium rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Channel Form Modal */}
      {showForm && (
        <ChannelFormModal
          channel={editingChannel}
          onClose={() => {
            setShowForm(false);
            setEditingChannel(null);
          }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
