"""Additional API routes for the Sambot web app."""
import base64
import os
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from groq import Groq

router = APIRouter()

CHAT_MODELS = [
    {"id": "openai/gpt-oss-120b", "name": "GPT OSS 120B (Groq)"},
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
]

@router.get("/api/models")
def models():
    """Return the model choices available in Sambot's UI."""
    return {"models": CHAT_MODELS, "default": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")}

class VisionRequest(BaseModel):
    prompt: str = Field(default="Describe this image clearly and accurately.", max_length=4000)
    image_data_url: str = Field(max_length=12_000_000)

@router.post("/api/vision")
def vision(req: VisionRequest):
    """Analyze a browser-uploaded image using Groq vision."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return JSONResponse({"error": "GROQ_API_KEY is not configured on the server."}, status_code=503)
    try:
        if not req.image_data_url.startswith("data:image/") or ";base64," not in req.image_data_url:
            return JSONResponse({"error": "Please provide an image in a supported data-URL format."}, status_code=400)
        mime = req.image_data_url[5:].split(";", 1)[0]
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            return JSONResponse({"error": "Use a JPG, PNG, WEBP, or GIF image."}, status_code=415)
        encoded = req.image_data_url.split(",", 1)[1]
        try:
            raw_image = base64.b64decode(encoded, validate=True)
        except Exception:
            return JSONResponse({"error": "The uploaded image data is invalid."}, status_code=400)
        if len(raw_image) > 8 * 1024 * 1024:
            return JSONResponse({"error": "Image is too large. Please choose an image under 8 MB."}, status_code=413)
        client = Groq(api_key=key, timeout=60.0, max_retries=1)
        result = client.chat.completions.create(
            model=os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": req.prompt[:4000]},
                    {"type": "image_url", "image_url": {"url": req.image_data_url}},
                ],
            }],
            max_tokens=1200,
        )
        return {"reply": result.choices[0].message.content or "I couldn't produce an image description."}
    except Exception as exc:
        print(f"SAMBOT_VISION_ERROR: {type(exc).__name__}: {exc}")
        return JSONResponse({"error": "Image analysis failed. Please try a smaller supported image or try again later."}, status_code=502)
