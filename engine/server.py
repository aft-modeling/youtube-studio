from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from script_generator import generate_script
from reference_analyzer import analyze_reference
from voiceover import generate_voiceover
from visuals import generate_visuals

app = FastAPI(title="YouTube Studio Engine")

# CORS — allow requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScriptRequest(BaseModel):
    topic: str
    target_length_minutes: int = 10
    channel_niche: str = "general"
    reference_context: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/generate-script")
async def api_generate_script(req: ScriptRequest):
    result = await generate_script(
        topic=req.topic,
        target_length_minutes=req.target_length_minutes,
        channel_niche=req.channel_niche,
        reference_context=req.reference_context,
    )

    if "error" in result:
        return {"error": result["error"]}, 500

    return result


class ReferenceRequest(BaseModel):
    youtube_url: str


@app.post("/api/analyze-reference")
async def api_analyze_reference(req: ReferenceRequest):
    result = await analyze_reference(youtube_url=req.youtube_url)

    if "error" in result:
        return {"error": result["error"]}, 400

    return result


class VoiceoverRequest(BaseModel):
    script_text: str
    voice_id: str
    stability: float = 0.5
    similarity: float = 0.75


@app.post("/api/generate-voiceover")
async def api_generate_voiceover(req: VoiceoverRequest):
    result = await generate_voiceover(
        script_text=req.script_text,
        voice_id=req.voice_id,
        stability=req.stability,
        similarity=req.similarity,
    )

    if "error" in result:
        return {"error": result["error"]}, 500

    return result


class VisualsRequest(BaseModel):
    script_segments: list[dict]
    project_id: str = ""


@app.post("/api/generate-visuals")
async def api_generate_visuals(req: VisualsRequest):
    result = await generate_visuals(
        script_segments=req.script_segments,
        project_id=req.project_id,
    )

    if "error" in result:
        return {"error": result["error"]}, 500

    return result


@app.post("/api/generate-video")
async def generate_video():
    return {"message": "not implemented yet"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
