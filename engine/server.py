from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from script_generator import generate_script

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


@app.post("/api/generate-video")
async def generate_video():
    return {"message": "not implemented yet"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
