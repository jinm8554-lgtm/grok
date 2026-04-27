"""
Grok Aurora Studio - FastAPI Backend
Provides REST and WebSocket endpoints for image/video generation
Uses Playwright browser bridge to bypass x-statsig-id restriction
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from grok_client import GrokClient


# ── Models ────────────────────────────────────────────────────────────────────

class GenerateImageRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"
    quality: str = "standard"


class GenerateVideoRequest(BaseModel):
    prompt: str
    duration: int = 6
    aspect_ratio: str = "16:9"
    resolution: str = "480p"


class CookiesRequest(BaseModel):
    cookies: dict


class TestGenerateRequest(BaseModel):
    prompt: str = "a cute cat sitting on a windowsill"
    mode: str = "image"   # "image" or "video"


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Grok Aurora Studio", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_cookies: Optional[dict] = None

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Basic endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(str(html_file), media_type="text/html")
    return {"message": "Grok Aurora Studio - Open /static/index.html"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "grok-aurora-studio",
        "version": "2.0.0",
        "cookies_loaded": session_cookies is not None,
        "cookie_count": len(session_cookies) if session_cookies else 0,
    }


# ── Cookie management ─────────────────────────────────────────────────────────

@app.post("/api/cookies")
async def set_cookies(request: CookiesRequest):
    global session_cookies
    session_cookies = request.cookies
    return {
        "status": "ok",
        "message": "Cookies updated",
        "keys": list(session_cookies.keys())
    }


@app.get("/api/cookies")
async def get_cookies():
    return {
        "loaded": session_cookies is not None,
        "keys": list(session_cookies.keys()) if session_cookies else []
    }


# ── Test endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/test-generate")
async def test_generate(request: TestGenerateRequest):
    """
    Quick test endpoint: runs a real generation and returns all SSE events.
    Use this to verify the browser bridge is working end-to-end.
    """
    if not session_cookies:
        raise HTTPException(
            status_code=401,
            detail="No authentication cookies. POST to /api/cookies first."
        )

    events = []
    try:
        async with GrokClient(cookies=session_cookies) as client:
            if request.mode == "video":
                gen = client.generate_video(prompt=request.prompt)
            else:
                gen = client.generate_image(prompt=request.prompt)

            async for chunk in gen:
                event = json.loads(chunk)
                events.append(event)
                # Stop early once we have the final result
                if event.get("status") in ("complete", "error"):
                    break

        return {"ok": True, "events": events}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── REST generation endpoints ─────────────────────────────────────────────────

@app.post("/api/generate-image")
async def generate_image(request: GenerateImageRequest):
    if not session_cookies:
        raise HTTPException(status_code=401, detail="No authentication cookies.")

    results = []
    async with GrokClient(cookies=session_cookies) as client:
        async for chunk in client.generate_image(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality
        ):
            results.append(json.loads(chunk))

    return {"results": results}


@app.post("/api/generate-video")
async def generate_video(request: GenerateVideoRequest):
    if not session_cookies:
        raise HTTPException(status_code=401, detail="No authentication cookies.")

    results = []
    async with GrokClient(cookies=session_cookies) as client:
        async for chunk in client.generate_video(
            prompt=request.prompt,
            duration=request.duration,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution
        ):
            results.append(json.loads(chunk))

    return {"results": results}


# ── WebSocket endpoints ───────────────────────────────────────────────────────

@app.websocket("/ws/generate-image")
async def websocket_generate_image(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)

            if not session_cookies:
                await websocket.send_json({
                    "status": "error",
                    "message": "No authentication cookies. Please set cookies first."
                })
                continue

            async with GrokClient(cookies=session_cookies) as client:
                async for chunk in client.generate_image(
                    prompt=request.get("prompt", ""),
                    aspect_ratio=request.get("aspect_ratio", "1:1"),
                    quality=request.get("quality", "standard")
                ):
                    await websocket.send_text(chunk)

    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        await websocket.close()


@app.websocket("/ws/generate-video")
async def websocket_generate_video(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)

            if not session_cookies:
                await websocket.send_json({
                    "status": "error",
                    "message": "No authentication cookies. Please set cookies first."
                })
                continue

            async with GrokClient(cookies=session_cookies) as client:
                async for chunk in client.generate_video(
                    prompt=request.get("prompt", ""),
                    duration=request.get("duration", 6),
                    aspect_ratio=request.get("aspect_ratio", "16:9"),
                    resolution=request.get("resolution", "480p")
                ):
                    await websocket.send_text(chunk)

    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        await websocket.close()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    static_dir.mkdir(exist_ok=True)
    print("Starting Grok Aurora Studio v2 (Playwright bridge)...")
    print("Open http://localhost:8000 in your browser")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
