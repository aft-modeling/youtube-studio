import { supabase } from "@/lib/supabase";

export async function GET() {
  const { data: channels, error } = await supabase
    .from("channels")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  // Get project counts for each channel
  const { data: counts } = await supabase
    .from("projects")
    .select("channel_id");

  const countMap: Record<string, number> = {};
  if (counts) {
    for (const row of counts) {
      countMap[row.channel_id] = (countMap[row.channel_id] || 0) + 1;
    }
  }

  const channelsWithCounts = channels.map((ch) => ({
    ...ch,
    project_count: countMap[ch.id] || 0,
  }));

  return Response.json(channelsWithCounts);
}

export async function POST(request: Request) {
  const body = await request.json();

  const { data, error } = await supabase
    .from("channels")
    .insert(body)
    .select()
    .single();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(data, { status: 201 });
}
