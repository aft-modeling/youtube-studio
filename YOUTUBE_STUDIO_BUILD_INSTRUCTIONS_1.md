# AI YouTube Studio — Complete Build Instructions for Claude Code

> **WHO IS READING THIS:** You are Claude Code, an AI coding assistant running inside VS Code. The human you are working with has **zero software engineering experience**. They can follow basic instructions like "run this command" or "paste your API key here," but they do not understand code, frameworks, or architecture. **Never ask them to write code.** **Never ask them to debug.** **Never use technical jargon without explaining it.** If something breaks, YOU fix it. If a decision needs to be made about architecture, YOU make it. The human's job is to provide API keys, test the app in their browser, and tell you if something looks wrong.

> **DEVELOPMENT ENVIRONMENT:** The human has Claude Code running in VS Code with MCP servers for **Vercel**, **GitHub**, and **Supabase** already connected. All deployment, database, and version control operations should go through these MCP servers. The human's computer has an RTX 4080 Super, Ryzen 9 7950X3D, 32GB RAM, and 2TB SSD running Windows.

> **WHAT WE ARE BUILDING:** A full-stack web application called **"YouTube Studio"** that automates the production of faceless YouTube videos. The user inputs a topic or a YouTube reference URL, and the app generates a complete video with AI voiceover, stock footage, AI-generated visuals, animated word-by-word captions, and background music. Output is a downloadable MP4 file ready for upload to YouTube.

---

## TABLE OF CONTENTS

1. [Project Overview & Architecture](#milestone-0-understand-the-project)
2. [Milestone 1: Project Scaffolding & Database](#milestone-1-project-scaffolding--database)
3. [Milestone 2: Channel Management System](#milestone-2-channel-management-system)
4. [Milestone 3: Script Generation Engine](#milestone-3-script-generation-engine)
5. [Milestone 4: Reference Video Analyzer](#milestone-4-reference-video-analyzer)
6. [Milestone 5: Voiceover Generation Pipeline](#milestone-5-voiceover-generation-pipeline)
7. [Milestone 6: Visual Asset Pipeline](#milestone-6-visual-asset-pipeline)
8. [Milestone 7: Caption Generator](#milestone-7-caption-generator)
9. [Milestone 8: Video Assembly Engine](#milestone-8-video-assembly-engine)
10. [Milestone 9: Thumbnail Generator](#milestone-9-thumbnail-generator)
11. [Milestone 10: Full Video Creation Wizard UI](#milestone-10-full-video-creation-wizard-ui)
12. [Milestone 11: Batch Processing & Queue System](#milestone-11-batch-processing--queue-system)
13. [Milestone 12: Polish, Settings & Final QA](#milestone-12-polish-settings--final-qa)
14. [API Keys & Services Reference](#api-keys--services-the-human-needs-to-provide)
15. [Tech Stack Reference](#tech-stack-reference)

---

## MILESTONE 0: UNDERSTAND THE PROJECT

**Do NOT write any code for this milestone.** Just read and understand.

### What the app does (user's perspective)

1. The user opens the app in their browser
2. They have pre-configured "channels" — each channel represents a YouTube channel with its own branding, voice, caption style, and niche
3. To make a video, the user clicks "New Video," selects a channel, and either:
   - Pastes a YouTube URL of a reference video they want to recreate (new original script inspired by the reference)
   - Types a topic/title to generate a video from scratch
4. The app generates a script. The user can read, edit, and approve it
5. Once approved, the app automatically:
   - Generates AI voiceover audio with ElevenLabs
   - Finds/downloads stock footage and AI-generated images matching the script
   - Creates word-by-word animated captions (Hormozi style)
   - Selects and ducks background music under the voiceover
   - Assembles everything into a final 1080p MP4
6. The user previews the video, downloads the MP4, and uploads it to YouTube manually

### Architecture overview

```
┌─────────────────────────────────────────────────┐
│                 FRONTEND (Next.js)               │
│         Hosted on Vercel (or localhost)           │
│                                                   │
│  ┌───────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │ Dashboard  │ │ Channels │ │ Video Wizard    │ │
│  │ (projects) │ │ Manager  │ │ (step-by-step)  │ │
│  └───────────┘ └──────────┘ └─────────────────┘ │
└────────────────────┬────────────────────────────┘
                     │ API Routes
                     ▼
┌─────────────────────────────────────────────────┐
│            BACKEND (Next.js API Routes +         │
│            Python workers on local machine)       │
│                                                   │
│  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ API Routes   │  │ Python Video Engine        │ │
│  │ (Next.js)    │  │ (runs locally via child    │ │
│  │              │◄─┤  process or local server)  │ │
│  └──────┬───────┘  │                            │ │
│         │          │ • script_generator.py       │ │
│         │          │ • reference_analyzer.py     │ │
│         │          │ • voiceover.py              │ │
│         │          │ • visuals.py                │ │
│         │          │ • captions.py               │ │
│         │          │ • assembler.py              │ │
│         │          │ • thumbnail.py              │ │
│         │          └───────────────────────────┘ │
└─────────┼───────────────────────────────────────┘
          │
          ▼
┌─────────────────────┐    ┌──────────────────────┐
│  Supabase            │    │ External APIs         │
│  • PostgreSQL DB     │    │ • Anthropic (Claude)  │
│  • File Storage      │    │ • ElevenLabs          │
│  • Auth (optional)   │    │ • Pexels              │
│                      │    │ • Replicate (Flux)    │
└─────────────────────┘    └──────────────────────┘
```

### Critical architecture decision: local Python backend

The video processing (FFmpeg, MoviePy, AI generation) is **too heavy and too slow** to run in Vercel serverless functions (they have a 60-second timeout and limited resources). Instead:

- The **Next.js frontend and API routes** can be deployed on Vercel for the UI
- The **Python video engine** runs as a **local FastAPI server** on the user's Windows machine
- The Next.js API routes call the local Python server to trigger video generation jobs
- The Python server processes jobs in the background and updates status in Supabase
- The frontend polls Supabase for job status updates

**In development**, everything runs locally (Next.js dev server + Python FastAPI server). **In production**, the Next.js app can optionally be deployed to Vercel, but the Python backend always runs locally because it needs the GPU and local FFmpeg.

### File structure

```
youtube-studio/
├── frontend/                    # Next.js app
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   │   ├── page.tsx         # Dashboard
│   │   │   ├── channels/        # Channel management
│   │   │   ├── projects/        # Video projects
│   │   │   └── api/             # API routes (proxy to Python backend)
│   │   ├── components/          # React components
│   │   ├── lib/                 # Utilities, Supabase client, etc.
│   │   └── styles/              # Global styles
│   ├── public/                  # Static assets
│   ├── package.json
│   └── next.config.js
├── engine/                      # Python video engine
│   ├── server.py                # FastAPI server entry point
│   ├── script_generator.py      # Claude API script generation
│   ├── reference_analyzer.py    # YouTube video analysis
│   ├── voiceover.py             # ElevenLabs TTS + audio enhancement
│   ├── visuals.py               # Stock footage + AI image sourcing
│   ├── captions.py              # Animated caption generation (ASS format)
│   ├── assembler.py             # FFmpeg video assembly
│   ├── thumbnail.py             # AI thumbnail generation
│   ├── music.py                 # Background music selection + ducking
│   ├── config.py                # API keys and configuration
│   ├── requirements.txt         # Python dependencies
│   └── assets/                  # Default assets
│       ├── fonts/               # Caption fonts
│       └── music/               # Royalty-free background tracks
├── supabase/                    # Database migrations
│   └── migrations/
├── .env.local                   # Environment variables (API keys)
├── .gitignore
└── README.md
```

---

## MILESTONE 1: PROJECT SCAFFOLDING & DATABASE

**Goal:** Set up the complete project structure, install all dependencies, connect to Supabase, and verify everything works.

**Estimated time:** 1–2 hours

### Step 1.1: Create the project repository

Create a new GitHub repository called `youtube-studio` using the GitHub MCP server. Clone it locally.

### Step 1.2: Set up the Next.js frontend

Inside the repo, create a Next.js app in the `frontend/` directory:
- Use the App Router (not Pages Router)
- Use TypeScript
- Use Tailwind CSS for styling
- Install these additional packages: `@supabase/supabase-js`, `@supabase/ssr`, `lucide-react` (for icons), `zustand` (for state management), `sonner` (for toast notifications)

### Step 1.3: Set up the Python engine

Inside the repo, create the `engine/` directory with:
- A `requirements.txt` containing:
  ```
  fastapi==0.115.0
  uvicorn==0.30.0
  anthropic==0.40.0
  elevenlabs==1.15.0
  requests==2.32.0
  moviepy==2.1.2
  pydub==0.25.1
  Pillow==11.1.0
  yt-dlp==2025.3.31
  youtube-transcript-api==0.6.3
  replicate==1.0.4
  python-dotenv==1.0.1
  aiofiles==24.1.0
  aiohttp==3.11.0
  noisereduce==3.0.3
  numpy==2.2.0
  ```
- A `server.py` that creates a FastAPI app with:
  - `GET /health` — returns `{"status": "ok"}` (used to verify the server is running)
  - `POST /api/generate-video` — placeholder that returns `{"message": "not implemented yet"}`
  - CORS middleware allowing requests from `localhost:3000` and any Vercel deployment URL
  - The server runs on port `8000`

- A `config.py` that loads API keys from environment variables (or a `.env` file using `python-dotenv`):
  ```python
  # Required API keys (loaded from .env file or environment)
  ANTHROPIC_API_KEY = ""
  ELEVENLABS_API_KEY = ""
  PEXELS_API_KEY = ""
  REPLICATE_API_TOKEN = ""
  SUPABASE_URL = ""
  SUPABASE_SERVICE_KEY = ""
  ```

### Step 1.4: Set up Supabase database

Using the Supabase MCP server, create these tables:

**Table: `channels`**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK, default gen_random_uuid()) | |
| name | text, NOT NULL | Channel display name |
| niche | text | e.g., "personal finance", "health" |
| elevenlabs_voice_id | text | Voice ID from ElevenLabs |
| voice_stability | float, default 0.5 | ElevenLabs stability setting |
| voice_similarity | float, default 0.75 | ElevenLabs similarity setting |
| caption_font | text, default 'Montserrat' | Font for animated captions |
| caption_color | text, default '#FFFFFF' | Primary caption color (hex) |
| caption_highlight_color | text, default '#FFD700' | Highlight color for active word |
| caption_position | text, default 'bottom' | 'bottom', 'center', or 'top' |
| caption_font_size | int, default 48 | Caption font size in pixels |
| default_video_length | text, default '10' | Target length in minutes |
| intro_text | text | Optional intro text overlay |
| outro_text | text | Optional outro text/CTA |
| music_genre | text, default 'ambient' | Preferred background music style |
| music_volume | float, default 0.15 | Background music volume (0-1) |
| notes | text | Free-form notes |
| created_at | timestamptz, default now() | |
| updated_at | timestamptz, default now() | |

**Table: `projects`**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK, default gen_random_uuid()) | |
| channel_id | uuid, FK → channels.id | |
| title | text, NOT NULL | Video title |
| status | text, default 'draft' | 'draft', 'scripting', 'voiceover', 'visuals', 'assembling', 'complete', 'error' |
| reference_url | text | YouTube URL if using reference |
| topic | text | Topic if generating from scratch |
| script | text | Generated/edited script |
| script_segments | jsonb | Structured script with visual cues and timestamps |
| voiceover_url | text | Path/URL to generated audio file |
| word_timestamps | jsonb | Word-level timestamps from ElevenLabs |
| visual_assets | jsonb | Array of visual asset references |
| caption_file_url | text | Path to ASS subtitle file |
| thumbnail_urls | jsonb | Array of generated thumbnail paths |
| final_video_url | text | Path to final MP4 |
| duration_seconds | int | Final video duration |
| error_message | text | Error details if status is 'error' |
| metadata | jsonb | Any additional metadata |
| created_at | timestamptz, default now() | |
| updated_at | timestamptz, default now() | |

**Table: `music_tracks`**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK, default gen_random_uuid()) | |
| name | text, NOT NULL | Track name |
| file_path | text, NOT NULL | Local path to the audio file |
| genre | text | 'ambient', 'cinematic', 'upbeat', 'lo-fi', 'dramatic' |
| duration_seconds | int | Track length |
| bpm | int | Beats per minute |
| mood | text | 'calm', 'energetic', 'dark', 'inspiring', 'neutral' |

Enable Row Level Security (RLS) on all tables but create policies that allow all operations (since this is a single-user local tool, we don't need auth restrictions).

### Step 1.5: Create the `.env.local` file

Create a `.env.local` file in the project root with placeholder values. **Tell the human they need to fill in their actual API keys:**

```env
# === SUPABASE ===
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# === ANTHROPIC (Claude API) ===
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# === ELEVENLABS ===
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# === PEXELS (free stock footage/images) ===
PEXELS_API_KEY=your_pexels_api_key_here

# === REPLICATE (for Flux AI image generation) ===
REPLICATE_API_TOKEN=your_replicate_api_token_here

# === LOCAL PYTHON ENGINE ===
PYTHON_ENGINE_URL=http://localhost:8000
```

Also create an `engine/.env` file that mirrors the relevant keys for the Python backend.

### Step 1.6: Create a shared `.gitignore`

Make sure the `.gitignore` excludes:
- `.env*` (all env files)
- `node_modules/`
- `__pycache__/`
- `.next/`
- `engine/output/` (generated video files)
- `engine/temp/` (temporary processing files)
- `engine/assets/music/*.mp3` (user-supplied music files)
- `*.mp4`
- `*.mp3` in output directories

### Step 1.7: Verify everything works

1. Start the Next.js dev server (`cd frontend && npm run dev`) — it should load at `http://localhost:3000` with a blank page
2. Start the Python server (`cd engine && python server.py`) — it should start at `http://localhost:8000`
3. Hit `http://localhost:8000/health` in the browser — should return `{"status": "ok"}`
4. Verify Supabase connection by querying the `channels` table from the Next.js app (should return empty array)

### Step 1.8: Commit and push to GitHub

Use the GitHub MCP server to commit all files with the message: `"Milestone 1: Project scaffolding, database schema, and base setup"`

### ✅ Milestone 1 is complete when:
- [ ] Next.js app loads in browser at localhost:3000
- [ ] Python FastAPI server responds at localhost:8000/health
- [ ] Supabase tables are created and accessible
- [ ] All dependencies are installed
- [ ] Code is committed to GitHub

---

## MILESTONE 2: CHANNEL MANAGEMENT SYSTEM

**Goal:** Build the UI for creating, editing, and managing YouTube channels. Each channel stores its unique configuration (voice, caption style, niche, etc.).

**Estimated time:** 2–3 hours

### What to build

**Page: `/channels`** — Lists all channels in a clean card/grid layout. Each card shows:
- Channel name and niche
- Voice ID (truncated)
- Caption style preview (colored dot showing the highlight color)
- Number of videos produced (count from projects table)
- Created date
- Edit and delete buttons

**Modal/Page: Add/Edit Channel** — A form with all the fields from the `channels` table:
- Channel name (text input, required)
- Niche (text input with suggestions dropdown: "personal finance", "health & wellness", "technology", "true crime", "history", "science", "business", "real estate", "self improvement", "psychology")
- ElevenLabs Voice ID (text input — the human will paste this from their ElevenLabs dashboard)
- Voice stability slider (0 to 1, default 0.5)
- Voice similarity slider (0 to 1, default 0.75)
- Caption settings section:
  - Font dropdown (Montserrat, Bebas Neue, Oswald, Poppins, Roboto Condensed)
  - Primary color picker (default white)
  - Highlight color picker (default gold/yellow)
  - Position toggle (bottom / center / top)
  - Font size slider (32–72px, default 48)
- Default video length dropdown (8, 10, 12, 15, 20, 25, 30 minutes)
- Intro text (optional text area)
- Outro text / CTA (optional text area)
- Background music genre dropdown (ambient, cinematic, upbeat, lo-fi, dramatic)
- Background music volume slider (0 to 0.5, default 0.15)
- Notes (optional text area)

### UI/UX requirements

- Dark theme (dark gray/near-black background, not pure black)
- Clean, modern design. Think "professional SaaS tool," not "flashy consumer app"
- Use a color palette: dark navy/charcoal backgrounds (#0f1117, #1a1d27), blue accent (#3b82f6), and white/light gray text
- The channel cards should look polished — rounded corners, subtle borders, hover effects
- Form inputs should have dark backgrounds with light text
- Use `sonner` for success/error toasts after saving
- Responsive layout (works on desktop, doesn't need to be mobile-perfect)

### Data operations

- All CRUD operations go through Next.js API routes that talk to Supabase
- API routes: `GET /api/channels`, `POST /api/channels`, `PUT /api/channels/[id]`, `DELETE /api/channels/[id]`
- Deleting a channel should show a confirmation dialog (it will also delete all associated projects)

### Step 2.1: Build the Supabase client utility

Create `frontend/src/lib/supabase.ts` with a properly configured Supabase client for both server-side and client-side use.

### Step 2.2: Build the API routes

Create the CRUD API routes for channels.

### Step 2.3: Build the Channels page

Create the main channels list page with add/edit/delete functionality.

### Step 2.4: Test

- Create 2-3 test channels with different configurations
- Edit a channel and verify changes persist
- Delete a channel and verify it's removed

### Step 2.5: Commit

`"Milestone 2: Channel management system with full CRUD"`

### ✅ Milestone 2 is complete when:
- [ ] Can create a new channel with all settings
- [ ] Channels list shows all channels with their details
- [ ] Can edit any channel's settings
- [ ] Can delete a channel with confirmation
- [ ] All data persists in Supabase

---

## MILESTONE 3: SCRIPT GENERATION ENGINE

**Goal:** Build the Python module that takes a topic (and optionally a target video length) and generates a structured YouTube script using the Claude API. The script includes visual cues for each segment.

**Estimated time:** 2–3 hours

### What to build

**File: `engine/script_generator.py`**

This module:
1. Takes inputs: `topic` (string), `target_length_minutes` (int), `channel_niche` (string), `reference_context` (optional string — transcript and metadata from a reference video)
2. Calls the Anthropic Claude API (model: `claude-sonnet-4-20250514`) with a carefully crafted prompt
3. Returns a structured script object

### The Claude prompt for script generation

This is the most important prompt in the entire system. It must produce scripts that are genuinely engaging, not generic AI slop. Here is the prompt template to implement:

```
SYSTEM PROMPT:
You are an elite YouTube scriptwriter who specializes in faceless educational and entertainment content. Your scripts consistently achieve 50%+ audience retention rates. You write in a conversational, engaging, slightly informal tone. You never sound like a textbook or a corporate presentation. You sound like a smart friend explaining something fascinating over coffee.

Your scripts follow a precise structure designed to maximize viewer retention:
1. HOOK (first 30 seconds / ~75 words): Open with a bold claim, surprising statistic, counterintuitive statement, or irresistible question that creates a curiosity gap. The viewer must feel compelled to keep watching. Never start with "In this video..." or "Today we're going to..."
2. CONTEXT (30 sec - 1.5 min / ~150 words): Briefly establish why this topic matters to the viewer personally. Create stakes. Make them feel like they NEED this information.
3. CORE CONTENT (main body / varies): Deliver the main value in 4-7 distinct sections. Each section needs:
   - A mini-hook or transition that re-engages attention
   - One clear point or insight
   - A concrete example, story, or data point
   - A "pattern interrupt" every 60-90 seconds (surprising fact, rhetorical question, hypothetical scenario, tonal shift)
4. CLIMAX (1-2 min before the end): The single most valuable, surprising, or mind-blowing insight. Reward viewers who stayed the whole time.
5. CTA + OUTRO (last 30 seconds / ~75 words): Brief, natural call to action. Don't beg for likes/subscribes — give them a reason. Suggest they'll enjoy another video on a related topic.

CRITICAL RULES:
- Use short sentences. Vary sentence length for rhythm.
- Use "you" and "your" constantly. Make it personal.
- Every 60-90 seconds of narration, include a pattern interrupt.
- Never use clichés like "buckle up", "dive in", "without further ado", "game-changer", or "let's get started."
- Write for SPOKEN delivery. Read it out loud in your head. If it sounds awkward spoken, rewrite it.
- Include [VISUAL: description] tags throughout the script. Place one after every 2-3 sentences. These describe what should be shown on screen (stock footage, graphics, text overlays, etc.)
- Include [TRANSITION] tags between major sections.

OUTPUT FORMAT:
Return ONLY valid JSON with this structure (no markdown, no backticks, no extra text):
{
  "title": "Compelling video title (with power words, numbers, or curiosity gaps)",
  "hook_text": "The opening hook as a standalone text (for thumbnail/title optimization)",
  "estimated_duration_minutes": <number>,
  "segments": [
    {
      "segment_number": 1,
      "segment_type": "hook" | "context" | "content" | "climax" | "cta",
      "segment_title": "Brief title for this segment",
      "narration": "The actual narration text for this segment...",
      "visual_cues": [
        "Description of what should be shown on screen during this segment",
        "Can have multiple visual cues per segment"
      ],
      "estimated_duration_seconds": <number>,
      "pattern_interrupt": "Optional: description of the pattern interrupt in this segment" | null
    }
  ],
  "tags": ["relevant", "youtube", "seo", "tags"],
  "description": "A YouTube description (2-3 sentences summarizing the video, with relevant keywords)"
}

USER PROMPT:
Write a YouTube script for a {channel_niche} channel.
Topic: {topic}
Target video length: {target_length_minutes} minutes (approximately {target_word_count} words of narration at 150 words per minute)

{IF reference_context EXISTS:}
Here is a reference for the style and topic coverage. DO NOT copy this. Use it only as inspiration for topic coverage and structure. Write a completely original script with different examples, different data points, and a fresh perspective:
---
{reference_context}
---
{END IF}
```

### The structured response

The script generator should:
1. Call Claude with the above prompt
2. Parse the JSON response
3. Validate the structure (all required fields present)
4. Calculate total word count and estimated duration
5. If the script is too short or too long (more than 20% off target), make a second API call asking Claude to adjust the length
6. Return the structured script object

### FastAPI endpoint

Add to `server.py`:
- `POST /api/generate-script` — accepts `{ topic, target_length_minutes, channel_niche, reference_context? }`, returns the structured script JSON

### Error handling

- If the Claude API returns an error, return a clear error message
- If the JSON parsing fails (Claude sometimes wraps JSON in markdown), strip any markdown backticks and retry parsing
- If the script is dramatically wrong length, retry once with explicit length correction

### Step 3.1: Implement script_generator.py
### Step 3.2: Add the FastAPI endpoint
### Step 3.3: Test with 3 different topics and verify script quality
### Step 3.4: Commit

`"Milestone 3: Script generation engine with Claude API"`

### ✅ Milestone 3 is complete when:
- [ ] Can send a POST request to `/api/generate-script` with a topic and get back a structured script
- [ ] Scripts follow the hook/context/content/climax/CTA structure
- [ ] Scripts include [VISUAL] cues for each segment
- [ ] Scripts are approximately the right length for the target duration
- [ ] Error handling works (bad API key returns clear error, not a crash)

---

## MILESTONE 4: REFERENCE VIDEO ANALYZER

**Goal:** Build the module that takes a YouTube URL, extracts the transcript and metadata, and prepares it as context for the script generator.

**Estimated time:** 1–2 hours

### What to build

**File: `engine/reference_analyzer.py`**

This module:
1. Takes a YouTube URL as input
2. Extracts the video transcript (using `youtube-transcript-api`)
3. Extracts video metadata (title, description, duration, tags, view count) using `yt-dlp`
4. Combines transcript + metadata into a structured reference context string
5. Returns this context for use by the script generator

### Implementation details

- Use `youtube-transcript-api` first (it's faster and doesn't require downloading the video). Fall back to `yt-dlp` subtitle extraction if the API fails.
- The reference context should be formatted as:
  ```
  REFERENCE VIDEO ANALYSIS:
  Title: {title}
  Duration: {duration}
  View Count: {views}
  Description: {description}
  
  TRANSCRIPT:
  {full transcript text}
  
  KEY TOPICS COVERED:
  {Use Claude to extract 5-10 key topics from the transcript — this helps the script generator understand what to cover}
  ```
- If the transcript is very long (>10,000 words), summarize it using Claude before including it (to stay within token limits)

### FastAPI endpoint

Add to `server.py`:
- `POST /api/analyze-reference` — accepts `{ youtube_url }`, returns `{ title, duration, view_count, reference_context, topics }`

### Error handling

- If the video has no transcript available (some videos don't have captions), return a clear message suggesting the user try a different reference video
- If `yt-dlp` can't access the video (private, age-restricted, etc.), return a clear error
- Handle non-YouTube URLs gracefully

### Step 4.1: Implement reference_analyzer.py
### Step 4.2: Add the FastAPI endpoint
### Step 4.3: Test with 3 different YouTube URLs (different lengths, niches)
### Step 4.4: Commit

`"Milestone 4: Reference video analyzer with transcript extraction"`

### ✅ Milestone 4 is complete when:
- [ ] Can input any public YouTube URL and get back transcript + metadata
- [ ] Reference context is formatted cleanly for the script generator
- [ ] Long transcripts are properly summarized
- [ ] Clear error messages for videos without transcripts
- [ ] Works with various YouTube URL formats (youtube.com, youtu.be, with/without timestamps)

---

## MILESTONE 5: VOICEOVER GENERATION PIPELINE

**Goal:** Build the module that takes a script, generates speech audio via ElevenLabs, extracts word-level timestamps, and enhances the audio quality.

**Estimated time:** 2–3 hours

### What to build

**File: `engine/voiceover.py`**

This module:
1. Takes the script text (combined narration from all segments) and an ElevenLabs voice ID
2. Calls the ElevenLabs Text-to-Speech API with `word-level timestamps` enabled
3. Receives the audio file (MP3) and the timestamp data
4. Enhances the audio:
   - Normalize volume levels
   - Apply light compression (reduce dynamic range so quiet parts aren't too quiet)
   - Apply noise reduction (remove any AI artifacts)
   - Optional: add subtle warmth/presence EQ
5. Saves the enhanced audio file
6. Returns the audio file path and word-level timestamps

### ElevenLabs API integration

- Use the ElevenLabs Python SDK
- Use the `text-to-speech` endpoint with `with_timestamps` parameter
- Model: `eleven_multilingual_v2` (highest quality)
- The API returns both the audio bytes and an `alignment` object containing word-level timestamps
- Voice settings to use: the `stability` and `similarity_boost` values from the channel configuration

### Audio enhancement pipeline

Use `pydub` and `noisereduce` (via numpy arrays):
1. Load the raw ElevenLabs audio
2. Normalize to -3dB
3. Apply noise reduction using `noisereduce.reduce_noise()`
4. Apply gentle compression (reduce peaks above -10dB)
5. Optional: high-pass filter at 80Hz to remove rumble
6. Export as high-quality MP3 (192kbps) and WAV (for FFmpeg assembly)

### Handling long scripts

ElevenLabs has a character limit per request (varies by plan). For scripts longer than 5,000 characters:
- Split the script at sentence boundaries into chunks under the limit
- Generate audio for each chunk separately
- Concatenate the audio files using `pydub`
- Adjust timestamps for subsequent chunks (offset by the duration of previous chunks)

### FastAPI endpoint

Add to `server.py`:
- `POST /api/generate-voiceover` — accepts `{ script_text, voice_id, stability, similarity }`, returns `{ audio_file_path, word_timestamps, duration_seconds }`

### Step 5.1: Implement voiceover.py
### Step 5.2: Add the FastAPI endpoint
### Step 5.3: Test with a short script (30 seconds) and verify audio quality
### Step 5.4: Test with a long script (5+ minutes) and verify chunking works
### Step 5.5: Commit

`"Milestone 5: Voiceover generation with ElevenLabs + audio enhancement"`

### ✅ Milestone 5 is complete when:
- [ ] Can generate voiceover audio from script text
- [ ] Word-level timestamps are extracted and accurate
- [ ] Audio is enhanced (normalized, noise reduced)
- [ ] Long scripts are properly chunked and concatenated
- [ ] Audio sounds natural and clean (not robotic, no artifacts)

---

## MILESTONE 6: VISUAL ASSET PIPELINE

**Goal:** Build the module that takes the script's visual cues and finds/generates appropriate visual assets (stock footage, stock images, AI-generated images).

**Estimated time:** 3–4 hours

### What to build

**File: `engine/visuals.py`**

This module:
1. Takes the structured script (with visual cues and timestamps for each segment)
2. For each visual cue:
   - Determines whether it needs **stock footage** (video), **stock image**, or **AI-generated image**
   - Searches Pexels API for stock footage/images
   - If stock footage isn't good enough or the visual is too specific/abstract, generates an image using Replicate (Flux model)
3. Downloads/saves all visual assets locally
4. Returns a timeline mapping: which visual plays during which time range of the voiceover

### Visual type decision logic

For each `visual_cue` string from the script:
- If the cue describes something **concrete and filmable** (e.g., "city skyline at night", "person running", "ocean waves") → search Pexels for stock **video** first, then stock **image** as fallback
- If the cue describes something **abstract or conceptual** (e.g., "the concept of compound interest", "brain neural pathways firing") → generate with AI (Replicate/Flux)
- If the cue describes a **text overlay or statistic** (e.g., "show text: $48,000 average loss") → create a simple text-on-dark-background image using Pillow

Use Claude (a quick, cheap API call to Haiku/Sonnet) to classify each visual cue into one of these three categories and generate the optimal search query for Pexels.

### Pexels API integration

- Pexels has both `/videos/search` and `/search` (images) endpoints
- Search with relevant keywords extracted from the visual cue
- Select the best result based on:
  - Relevance to the query
  - Resolution (prefer 1080p+)
  - For videos: duration (prefer clips longer than the segment duration so we can trim)
  - Orientation: landscape (16:9) only — reject portrait content
- Download the selected asset to `engine/temp/visuals/`
- If Pexels returns no good results, fall back to AI generation

### Replicate/Flux integration

- Use the Replicate Python SDK
- Model: `black-forest-labs/flux-1.1-pro` or the latest Flux model available
- Prompt: the visual cue text, enhanced with: "photorealistic, 16:9 aspect ratio, high quality, cinematic lighting, YouTube video screenshot style"
- Download the generated image

### Pillow text overlay generator

For text/statistic visual cues:
- Create a 1920x1080 dark background image
- Add the text centered with a clean, bold font
- Support basic formatting (large number/statistic on top, smaller context text below)

### Visual timeline mapping

The output should be an array of objects:
```json
[
  {
    "segment_number": 1,
    "start_time": 0.0,
    "end_time": 15.5,
    "asset_type": "video" | "image" | "ai_image" | "text_overlay",
    "asset_path": "/path/to/asset.mp4",
    "search_query": "what was searched",
    "source": "pexels" | "replicate" | "generated",
    "ken_burns": true,  // only for images — apply slow zoom effect
    "duration": 15.5
  }
]
```

### FastAPI endpoint

Add to `server.py`:
- `POST /api/generate-visuals` — accepts `{ script_segments, project_id }`, returns `{ visual_timeline }` and saves assets to disk

### Step 6.1: Implement the visual type classifier (Claude API call)
### Step 6.2: Implement Pexels search and download
### Step 6.3: Implement Replicate/Flux image generation
### Step 6.4: Implement Pillow text overlay generator
### Step 6.5: Implement the visual timeline mapper
### Step 6.6: Add the FastAPI endpoint
### Step 6.7: Test with a full script and verify visual quality/relevance
### Step 6.8: Commit

`"Milestone 6: Visual asset pipeline with Pexels + Flux + text overlays"`

### ✅ Milestone 6 is complete when:
- [ ] Visual cues are correctly classified (stock vs AI vs text)
- [ ] Pexels search returns relevant, landscape, high-quality results
- [ ] AI image generation produces good-quality images for abstract concepts
- [ ] Text overlays are clean and readable
- [ ] Visual timeline correctly maps each asset to the voiceover timestamps
- [ ] All assets download and save successfully

---

## MILESTONE 7: CAPTION GENERATOR

**Goal:** Build the module that creates Hormozi-style word-by-word animated captions synced to the voiceover.

**Estimated time:** 2–3 hours

### What to build

**File: `engine/captions.py`**

This module:
1. Takes the word-level timestamps from the voiceover module
2. Generates an ASS (Advanced SubStation Alpha) subtitle file with word-by-word animation
3. The style mimics the "Hormozi" / "CapCut auto-caption" style:
   - Words appear on screen synced to when they're spoken
   - The currently spoken word is highlighted (different color, slightly larger, or bold)
   - 2-4 words visible at a time (not the entire sentence)
   - Clean, bold font with outline/shadow for readability over any background
   - Positioned at the bottom-center (or wherever the channel config specifies)

### ASS subtitle format

ASS is the most flexible subtitle format for styled, animated text. FFmpeg can burn ASS subtitles directly into video.

The ASS file structure:
```
[Script Info]
Title: YouTube Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,60,1
Style: Highlight,Montserrat,52,&H0000D7FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
```

### Word grouping logic

Don't show one word at a time (too jittery) or full sentences (not engaging). Group words into chunks of 2-4 words based on natural speech patterns:
- Keep articles with their nouns ("the world", not "the" + "world")
- Keep prepositions with their objects ("in the morning")
- Break at natural pauses (commas, periods, semicolons)
- Each group should be visible for the duration of those words in the voiceover

### Highlight animation

For each word group, the currently-being-spoken word uses the `Highlight` style (different color, slightly larger). Previous words in the group use the `Default` style. Use ASS override tags:
```
{\rHighlight}currently_spoken{\rDefault} previous_word another_word
```

### Configuration from channel settings

The caption generator should accept these parameters (from the channel configuration):
- `font_name` — the font to use
- `font_size` — base font size
- `primary_color` — color for non-highlighted words (in ASS hex format: `&H00BBGGRR`)
- `highlight_color` — color for the active word
- `position` — bottom, center, or top (affects MarginV and Alignment)

### FastAPI endpoint

Add to `server.py`:
- `POST /api/generate-captions` — accepts `{ word_timestamps, caption_config }`, returns `{ caption_file_path }`

### Step 7.1: Implement the word grouping logic
### Step 7.2: Implement ASS file generation with animation
### Step 7.3: Add the FastAPI endpoint
### Step 7.4: Test by rendering captions on a sample video with FFmpeg and visually inspecting
### Step 7.5: Commit

`"Milestone 7: Animated word-by-word caption generator"`

### ✅ Milestone 7 is complete when:
- [ ] ASS subtitle file is generated with proper word-level timing
- [ ] Words are grouped naturally (2-4 words per display)
- [ ] Currently spoken word is visually highlighted (different color/size)
- [ ] Captions look clean and readable when burned into video
- [ ] Channel-specific settings (font, color, position) are applied correctly

---

## MILESTONE 8: VIDEO ASSEMBLY ENGINE

**Goal:** Build the FFmpeg-based module that combines all pieces (voiceover, visuals, captions, music) into the final MP4 video.

**Estimated time:** 3–4 hours

### What to build

**File: `engine/assembler.py`**

This is the core rendering engine. It takes:
- Voiceover audio file (WAV)
- Visual timeline (array of assets with start/end times)
- Caption file (ASS subtitles)
- Background music track (MP3)
- Channel configuration (music volume, intro/outro text)

And produces a final 1080p MP4 video.

### Assembly pipeline

The assembly happens in stages, each using FFmpeg:

**Stage 1: Prepare visual track**
For each visual asset in the timeline:
- **If video clip:** Trim to the required duration, resize/crop to 1920x1080, remove audio
- **If image:** Create a video clip from the still image at the required duration, apply Ken Burns effect (slow zoom from 100% to 110% or slow pan)
- **If AI-generated image:** Same as image but no Ken Burns unless configured
- Concatenate all visual clips in sequence with crossfade transitions (0.5 second crossfade between clips)

**Stage 2: Add voiceover audio**
- Overlay the voiceover audio onto the visual track
- Ensure audio and video are precisely synced (the visual timeline was built from the voiceover timestamps)

**Stage 3: Add background music**
- Loop the background music track if it's shorter than the video
- Apply volume ducking: the music should be at the configured volume level (e.g., 15%) but duck further when voiceover is playing
- Simple approach: set music to a consistent low volume. Advanced approach: use FFmpeg's `sidechaincompress` to duck the music when the voiceover is detected

Start with the simple approach (consistent low volume). Ducking can be added as an enhancement later.

**Stage 4: Burn in captions**
- Use FFmpeg's ASS subtitle filter to burn the animated captions into the video
- The ASS file handles all styling and animation

**Stage 5: Add intro/outro (optional)**
- If the channel has intro_text configured, add a 3-second title card at the beginning (text on dark background with fade-in)
- If the channel has outro_text configured, add a 5-second outro card at the end

**Stage 6: Final render**
- Encode as H.264 MP4 with AAC audio
- Resolution: 1920x1080
- Frame rate: 30fps
- Audio: 192kbps AAC stereo
- Video bitrate: 8-10 Mbps (high quality for YouTube)

### Ken Burns effect

For static images, apply a slow zoom to add movement:
```
ffmpeg -loop 1 -i image.png -vf "zoompan=z='min(zoom+0.0005,1.1)':d=300:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080" -t 10 -c:v libx264 output.mp4
```
Vary the zoom direction randomly: zoom in, zoom out, pan left-to-right, pan right-to-left.

### FFmpeg command construction

Build FFmpeg commands programmatically using Python subprocess. Do NOT use MoviePy for the final assembly — use FFmpeg directly for reliability and performance. MoviePy can be used for simple operations like getting video duration or extracting frames, but the main assembly should be pure FFmpeg.

The FFmpeg filter graph will be complex. Build it step by step and test each stage independently before combining.

### FastAPI endpoint

Add to `server.py`:
- `POST /api/assemble-video` — accepts `{ project_id, voiceover_path, visual_timeline, caption_path, music_path, channel_config }`, returns `{ video_path, duration_seconds }`

### FFmpeg installation note

**Tell the human:** "You need FFmpeg installed on your computer. If you don't have it, I'll install it for you." On Windows, install via: `winget install ffmpeg` or download from ffmpeg.org and add to PATH.

### Step 8.1: Implement visual track preparation (resize, crop, Ken Burns)
### Step 8.2: Implement clip concatenation with transitions
### Step 8.3: Implement audio mixing (voiceover + background music)
### Step 8.4: Implement caption burn-in
### Step 8.5: Implement intro/outro cards
### Step 8.6: Implement final render pipeline
### Step 8.7: Add the FastAPI endpoint
### Step 8.8: End-to-end test: full video from all components
### Step 8.9: Commit

`"Milestone 8: Video assembly engine with FFmpeg"`

### ✅ Milestone 8 is complete when:
- [ ] Can assemble a complete video from voiceover + visuals + captions + music
- [ ] Ken Burns effect works on static images
- [ ] Crossfade transitions between visual clips
- [ ] Background music plays at correct volume
- [ ] Captions are burned in with correct styling and timing
- [ ] Output is a clean 1080p MP4 at good quality
- [ ] Full video renders in under 10 minutes for a 10-minute video (on the user's hardware)

---

## MILESTONE 9: THUMBNAIL GENERATOR

**Goal:** Build the module that generates 2-3 thumbnail options for each video using AI image generation and text overlay.

**Estimated time:** 1–2 hours

### What to build

**File: `engine/thumbnail.py`**

This module:
1. Takes the video title, key topic, and channel branding
2. Generates 2-3 different background images using Replicate/Flux:
   - Each image should be visually striking, colorful, and relevant to the video topic
   - Prompt template: "YouTube thumbnail background, {topic_description}, vibrant colors, dramatic lighting, 16:9 aspect ratio, eye-catching, no text"
3. Adds text overlay using Pillow:
   - Large, bold title text (shortened to 3-5 impactful words)
   - Use a chunky, high-impact font (like Bebas Neue or Impact)
   - Add text outline/stroke for readability
   - Optional: Add small emoji or icon that relates to the topic
4. Outputs 2-3 thumbnail images at 1280x720 (YouTube's recommended thumbnail size)

### Text placement rules

- Text should take up roughly 40-60% of the thumbnail width
- Positioned to the left or right side (not centered — leaves room for the visual to breathe)
- Maximum 2 lines of text
- Use contrasting colors (white text with dark outline, or yellow text with dark outline)
- Font size: large enough to read on a mobile phone (which is where most YouTube viewers are)

### FastAPI endpoint

Add to `server.py`:
- `POST /api/generate-thumbnails` — accepts `{ title, topic, hook_text }`, returns `{ thumbnail_paths: [path1, path2, path3] }`

### Step 9.1: Implement AI background image generation
### Step 9.2: Implement text overlay with Pillow
### Step 9.3: Add the FastAPI endpoint
### Step 9.4: Test with several topics and verify thumbnail quality
### Step 9.5: Commit

`"Milestone 9: Thumbnail generator with AI backgrounds + text overlay"`

### ✅ Milestone 9 is complete when:
- [ ] Can generate 2-3 unique thumbnails per video
- [ ] Thumbnails are visually striking and relevant to the topic
- [ ] Text is readable, bold, and properly positioned
- [ ] Output is 1280x720 JPEG/PNG
- [ ] Generation takes under 60 seconds for all 3 thumbnails

---

## MILESTONE 10: FULL VIDEO CREATION WIZARD UI

**Goal:** Build the complete step-by-step video creation interface in the frontend that connects to all backend modules.

**Estimated time:** 4–6 hours

### What to build

This is the main feature of the app. A multi-step wizard that guides the user through creating a video.

**Page: `/projects/new`**

**Step 1: Setup**
- Select a channel from a dropdown (populated from Supabase)
- Choose input method: "Reference Video" or "Custom Topic"
- If Reference Video: text input for YouTube URL + "Analyze" button that calls the reference analyzer
- If Custom Topic: text input for the topic/title
- Target video length dropdown (8, 10, 12, 15, 20, 25, 30 minutes)
- "Generate Script" button

**Step 2: Script Review**
- Display the generated script in a rich text editor
- Show the structured segments with visual cues
- The user can:
  - Edit any text directly
  - Regenerate the entire script
  - Regenerate just the hook (common action)
  - Regenerate a specific segment
  - See estimated video duration
  - See word count
- "Approve Script & Continue" button

**Step 3: Production**
- This step runs automatically after script approval
- Show a progress tracker with these stages:
  1. ⏳ Generating voiceover... → ✅ Voiceover complete (X:XX duration)
  2. ⏳ Finding visual assets... → ✅ Visuals ready (X assets found)
  3. ⏳ Creating captions... → ✅ Captions generated
  4. ⏳ Assembling video... → ✅ Video assembled
  5. ⏳ Generating thumbnails... → ✅ Thumbnails ready
- Each stage updates in real-time as the Python backend reports progress
- Show elapsed time and estimated remaining time

**Implementation for real-time progress:**
- When the user clicks "Approve Script," the frontend calls a Next.js API route
- The API route calls the Python backend's `/api/generate-video-full` endpoint (which chains all steps)
- The Python backend updates the `projects` table in Supabase with status changes as it progresses
- The frontend polls the Supabase `projects` table every 2 seconds for status updates (use Supabase realtime subscriptions if possible, otherwise polling)

**Step 4: Review & Export**
- Video player showing the final MP4 (use an HTML5 `<video>` element)
- Display 2-3 thumbnail options side by side — user can select their favorite
- Details panel showing: duration, file size, word count
- Action buttons:
  - "Download MP4" — downloads the final video file
  - "Download Thumbnail" — downloads the selected thumbnail
  - "Download All" — downloads a zip with MP4 + thumbnail + script text file
  - "Open in Vegas Pro" — downloads a project-compatible export (or just the raw assets organized in a folder)
  - "Start New Video" — return to Step 1

**Page: `/projects`** (Dashboard)
- List all video projects in a table/grid
- Show: thumbnail preview, title, channel, status, created date, duration
- Filter by channel, status
- Sort by date
- Click any project to open it (resume from wherever it was left off, or review the finished video)

### Python backend: full pipeline endpoint

Add to `server.py`:
- `POST /api/generate-video-full` — accepts `{ project_id }` and runs the complete pipeline:
  1. Load project data from Supabase (script, channel config)
  2. Update status to "voiceover" → Generate voiceover → Save audio path to Supabase
  3. Update status to "visuals" → Generate visuals → Save visual timeline to Supabase
  4. Update status to "captions" → Generate captions → Save caption path to Supabase  
  5. Update status to "assembling" → Assemble video → Save video path to Supabase
  6. Generate thumbnails → Save thumbnail paths to Supabase
  7. Update status to "complete"
  
  If any step fails, update status to "error" with the error message.

### File serving

The Python backend needs to serve generated files (video, thumbnails, audio) so the frontend can access them:
- Add a static file route in FastAPI: `app.mount("/files", StaticFiles(directory="output"), name="files")`
- Generated files are saved to `engine/output/{project_id}/`
- The frontend accesses them via `http://localhost:8000/files/{project_id}/final.mp4`

### UI/UX requirements (same dark theme as Channels page)

- Progress tracker should have satisfying animations (checkmarks appearing, progress bars filling)
- Video player should be large and centered
- Thumbnail selection should have a clear "selected" state (border highlight)
- The script editor should be comfortable to read and edit (good font size, line spacing)
- Loading states should be clear — never leave the user wondering if something is happening

### Step 10.1: Build the full pipeline endpoint in Python
### Step 10.2: Build Step 1 UI (Setup)
### Step 10.3: Build Step 2 UI (Script Review)
### Step 10.4: Build Step 3 UI (Production Progress)
### Step 10.5: Build Step 4 UI (Review & Export)
### Step 10.6: Build the Projects Dashboard page
### Step 10.7: Connect everything — test full flow from URL input to downloaded MP4
### Step 10.8: Commit

`"Milestone 10: Complete video creation wizard with full pipeline integration"`

### ✅ Milestone 10 is complete when:
- [ ] Can create a video from a YouTube reference URL (full pipeline)
- [ ] Can create a video from a custom topic (full pipeline)
- [ ] Script editing works and changes are reflected in the final video
- [ ] Progress tracker updates in real-time during production
- [ ] Video preview plays in the browser
- [ ] Can download the final MP4 and thumbnails
- [ ] Projects dashboard shows all past and current projects
- [ ] The entire flow from input to MP4 takes under 60 minutes for a 10-minute video

---

## MILESTONE 11: BATCH PROCESSING & QUEUE SYSTEM

**Goal:** Enable the user to queue multiple videos for production and have them process sequentially in the background.

**Estimated time:** 2–3 hours

### What to build

Currently, the user creates one video at a time and waits for it to finish. For producing 10+ videos per day, they need to be able to queue up multiple videos and let them process while they do other things.

### Queue system

**Add a queue table to Supabase:**

**Table: `job_queue`**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | |
| project_id | uuid, FK → projects.id | |
| status | text | 'queued', 'processing', 'complete', 'error' |
| priority | int, default 0 | Higher = processed first |
| started_at | timestamptz | When processing began |
| completed_at | timestamptz | When processing finished |
| error_message | text | |
| created_at | timestamptz | |

### Python background worker

Modify the Python backend to run a background worker that:
1. Continuously polls the `job_queue` table for jobs with status 'queued'
2. Picks up the highest-priority queued job
3. Processes it through the full pipeline
4. Updates status to 'complete' or 'error'
5. Moves to the next job

Only process **one job at a time** (the RTX 4080 is powerful but video assembly is resource-intensive).

### "Quick Create" mode in the UI

Add a **"Quick Create"** button to the channels page or dashboard:
1. Select a channel
2. Paste a YouTube URL or topic
3. Click "Add to Queue" — this creates the project, generates the script (quick — takes a few seconds), and adds to the queue
4. The user can immediately add another video to the queue without waiting
5. A queue panel on the dashboard shows all queued/processing/complete jobs with progress

### Batch import

Add a **"Batch Create"** option:
1. User pastes multiple YouTube URLs or topics (one per line, up to 20)
2. Selects a channel
3. Sets the target video length
4. Clicks "Queue All"
5. The system creates all projects, generates scripts for all of them (sequentially), and adds them all to the queue

For batch mode, **skip the script review step** — scripts are auto-approved. The user can review and re-edit later if needed.

### Dashboard queue panel

Add a persistent "Queue" panel to the dashboard showing:
- Currently processing: title, channel, progress stage, elapsed time
- Queued: list of upcoming jobs with title and channel
- Recently completed: last 10 completed videos with quick-access download links
- Ability to reorder queue (drag-and-drop or up/down arrows)
- Ability to cancel queued jobs

### Step 11.1: Create the job_queue table in Supabase
### Step 11.2: Build the background worker in Python
### Step 11.3: Build the Quick Create UI
### Step 11.4: Build the Batch Create UI  
### Step 11.5: Build the Queue Dashboard panel
### Step 11.6: Test with 5 queued videos processing sequentially
### Step 11.7: Commit

`"Milestone 11: Batch processing and queue system"`

### ✅ Milestone 11 is complete when:
- [ ] Can queue multiple videos and they process one after another
- [ ] Queue panel shows real-time status of all jobs
- [ ] Quick Create allows adding videos to queue without waiting
- [ ] Batch Create accepts multiple URLs/topics at once
- [ ] Can cancel or reorder queued jobs
- [ ] Completed videos are accessible from the dashboard

---

## MILESTONE 12: POLISH, SETTINGS & FINAL QA

**Goal:** Add a settings page, polish the UI, fix bugs, and do a complete end-to-end quality check.

**Estimated time:** 2–3 hours

### What to build

**Settings Page (`/settings`)**
- **API Key Management:** Show which API keys are configured and their status (valid/invalid/missing). Add a "Test Connection" button for each API:
  - Anthropic: make a tiny test completion
  - ElevenLabs: fetch available voices list
  - Pexels: make a test search
  - Replicate: check account status
- **Default Settings:**
  - Default video resolution (1080p / 4K)
  - Default video bitrate
  - Default transition style (crossfade / cut / fade-to-black)
  - Default Ken Burns zoom percentage
  - Output directory path
- **Music Library:** Upload and manage background music tracks. Show the list from `music_tracks` table with playback preview. Allow adding new tracks (upload MP3, set genre/mood/BPM tags).
- **ElevenLabs Voice Browser:** A page/section that fetches all available voices from ElevenLabs and lets the user preview them. Shows voice name, labels, and a "Copy Voice ID" button for easy setup when creating channels.

### UI polish

Go through every page and ensure:
- Consistent dark theme throughout
- All buttons have hover/active states
- Loading states are shown during API calls (spinners, skeleton loaders)
- Error messages are displayed clearly in toast notifications
- Empty states have helpful messages (e.g., "No channels yet — create your first channel to get started")
- The app is responsive on a wide monitor (content doesn't stretch too wide — max-width container)

### Background music setup

**Tell the human:** "You need to add some royalty-free background music tracks to the `engine/assets/music/` directory. Here are free sources:
- YouTube Audio Library (studio.youtube.com → Audio Library → download tracks)
- Pixabay Music (pixabay.com/music/)
- Uppbeat (uppbeat.io — free tier available)

Download 5-10 tracks in different genres (ambient, cinematic, upbeat, lo-fi, dramatic) and place the MP3 files in `engine/assets/music/`. Then use the Settings page to tag each track with genre and mood."

### Font setup

**Tell the human:** "You need to download fonts for the captions. Download these from Google Fonts and place the .ttf files in `engine/assets/fonts/`:
- Montserrat Bold
- Bebas Neue
- Oswald Bold
- Poppins Bold
- Roboto Condensed Bold"

### End-to-end QA checklist

Run through the complete flow 3 times with different configurations:

**Test 1: Stock footage heavy video**
- Channel niche: personal finance
- Input: YouTube reference URL
- Video length: 10 minutes
- Verify: script quality, voiceover quality, visual relevance, caption sync, music volume, final output

**Test 2: AI visuals heavy video**
- Channel niche: science/technology
- Input: custom topic ("How quantum computers will change encryption forever")
- Video length: 12 minutes
- Verify: AI image quality, visual variety, timing

**Test 3: Batch processing test**
- Queue 3 videos across different channels
- Let them process unattended
- Verify all 3 complete successfully

### Step 12.1: Build the Settings page
### Step 12.2: Build the Music Library manager
### Step 12.3: Build the ElevenLabs Voice Browser
### Step 12.4: Polish UI across all pages
### Step 12.5: Run end-to-end QA tests
### Step 12.6: Fix all bugs found during QA
### Step 12.7: Final commit

`"Milestone 12: Settings, polish, and full QA — v1.0 complete"`

### ✅ Milestone 12 is complete when:
- [ ] Settings page shows API status and allows configuration
- [ ] Music library works (upload, tag, preview tracks)
- [ ] ElevenLabs voice browser lets user preview and copy voice IDs
- [ ] All UI is polished and consistent
- [ ] End-to-end flow works reliably 3/3 times
- [ ] No critical bugs remain
- [ ] The user can produce a complete 10-minute video in under 60 minutes

---

## API KEYS & SERVICES THE HUMAN NEEDS TO PROVIDE

Before starting Milestone 3, the human needs to sign up for these services and provide API keys. **Walk them through each one when you reach the milestone that needs it.**

| Service | What It's For | Where to Sign Up | Which Key to Copy | When Needed |
|---------|--------------|------------------|-------------------|-------------|
| **Anthropic** | Script generation (Claude API) | console.anthropic.com | API Key from Settings → API Keys | Milestone 3 |
| **ElevenLabs** | AI voiceover generation | elevenlabs.io | API Key from Profile → API Key | Milestone 5 |
| **Pexels** | Free stock footage & images | pexels.com/api | API Key from your account page | Milestone 6 |
| **Replicate** | AI image generation (Flux) | replicate.com | API Token from Account → API Tokens | Milestone 6 |
| **Supabase** | Database & file storage | supabase.com | Already connected via MCP | Milestone 1 |
| **Vercel** | Frontend hosting (optional) | vercel.com | Already connected via MCP | Milestone 1 |

**Important:** When the human provides an API key, save it to the `.env.local` file (for Next.js) AND the `engine/.env` file (for Python). Never hardcode API keys in source files. Never commit `.env` files to GitHub.

---

## TECH STACK REFERENCE

### Frontend
- **Next.js 14+** with App Router and TypeScript
- **Tailwind CSS** for styling
- **Zustand** for client state management
- **Supabase JS client** for database operations
- **Lucide React** for icons
- **Sonner** for toast notifications

### Backend
- **Python 3.11+** with FastAPI
- **FFmpeg** (must be installed on the system — used for all video operations)
- **Anthropic Python SDK** for Claude API
- **ElevenLabs Python SDK** for TTS
- **Replicate Python SDK** for Flux image generation
- **yt-dlp** for YouTube metadata extraction
- **youtube-transcript-api** for transcript extraction
- **pydub** for audio processing
- **noisereduce** for audio cleanup
- **Pillow** for image manipulation
- **MoviePy** for simple video operations (duration, frame extraction)

### Infrastructure
- **Supabase** — PostgreSQL database + file storage
- **GitHub** — version control
- **Vercel** — frontend deployment (optional, can run locally)
- **Local machine** — Python backend always runs locally (needs GPU + FFmpeg)

### System requirements (already met by the human's PC)
- Windows 10/11
- Python 3.11+
- Node.js 18+
- FFmpeg installed and in PATH
- 32GB+ RAM
- GPU with CUDA (RTX 4080 Super)
- 50GB+ free disk space for video processing

---

## IMPORTANT NOTES FOR CLAUDE CODE

1. **Always test after building.** Don't move to the next milestone until the current one is verified working.

2. **Keep the human informed.** After completing each step, tell the human what you did in plain English. Example: "I just built the page where you manage your YouTube channels. You can now go to localhost:3000/channels in your browser and try adding a channel."

3. **Handle errors gracefully.** Every API call should have try/catch. Every error should result in a clear user-facing message, not a crash.

4. **File paths on Windows.** Use `pathlib.Path` for all file paths in Python to ensure Windows compatibility. Use forward slashes in configuration.

5. **FFmpeg on Windows.** The human may need to install FFmpeg. Check if it's available with `ffmpeg -version` and guide the human through installation if needed.

6. **Python virtual environment.** Create a virtual environment for the Python engine to avoid dependency conflicts. Guide the human: "Run `python -m venv venv` in the engine folder, then `venv\Scripts\activate` on Windows."

7. **Concurrent development.** The human will need two terminal windows: one for `npm run dev` (frontend) and one for `python server.py` (backend). Explain this clearly.

8. **Git commits.** Commit after every milestone using the GitHub MCP server. This gives the human save points to return to.

9. **The human will say things like "Let's finish Milestone 5, I'm done for the day."** When they return, they'll say something like "Let's start Milestone 6." You should review where things left off and continue from there.

10. **If something breaks badly,** don't panic. Use `git log` to find the last working commit and offer to reset to it. The milestone-based commits make this safe.

11. **Keep the output directory organized.** Each project gets its own folder: `engine/output/{project_id}/` containing `script.json`, `voiceover.wav`, `visuals/`, `captions.ass`, `final.mp4`, and `thumbnails/`.

12. **Memory management.** Video processing uses a lot of RAM. Process one video at a time. Clean up temporary files after each video is complete.

13. **The human's machine runs Windows.** All commands, file paths, and instructions must be Windows-compatible. Use `python` not `python3`. Use `pip` not `pip3`. Path separators should use `pathlib` or forward slashes.
