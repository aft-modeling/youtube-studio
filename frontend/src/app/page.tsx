import Link from "next/link";
import { Tv, Video } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-white mb-2">Dashboard</h1>
      <p className="text-muted mb-8">
        Welcome to YouTube Studio. Get started by creating a channel.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
        <Link
          href="/channels"
          className="bg-card border border-border rounded-xl p-6 hover:bg-card-hover hover:border-accent/30 transition-all group"
        >
          <Tv className="w-8 h-8 text-accent mb-3 group-hover:scale-110 transition-transform" />
          <h2 className="text-white font-semibold mb-1">Channels</h2>
          <p className="text-muted text-sm">
            Manage your YouTube channels and their settings
          </p>
        </Link>
        <div className="bg-card border border-border rounded-xl p-6 opacity-50 cursor-not-allowed">
          <Video className="w-8 h-8 text-muted mb-3" />
          <h2 className="text-white font-semibold mb-1">Projects</h2>
          <p className="text-muted text-sm">Coming in a future milestone</p>
        </div>
      </div>
    </div>
  );
}
