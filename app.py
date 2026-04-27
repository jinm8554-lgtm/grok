"""
Grok Aurora Studio - FastAPI Backend
Provides REST and WebSocket endpoints for image/video generation
"""

from fastapi import FastAPI, WebSocket, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import aiohttp
from grok_client import GrokClient


# Models
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


# Initialize FastAPI app
app = FastAPI(title="Grok Aurora Studio", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active connections and session cookies
active_connections: dict = {}
session_cookies: Optional[dict] = None


# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve main HTML"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(str(html_file), media_type="text/html")
    return {"message": "Grok Aurora Studio - Open /static/index.html"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "grok-aurora-studio",
        "cookies_loaded": session_cookies is not None
    }


@app.post("/api/cookies")
async def set_cookies(request: CookiesRequest):
    """
    Set browser cookies for Grok authentication
    
    Expected cookies: sso, cf_clearance, etc.
    """
    global session_cookies
    session_cookies = request.cookies
    return {
        "status": "ok",
        "message": "Cookies updated",
        "keys": list(session_cookies.keys())
    }


@app.get("/api/cookies")
async def get_cookies():
    """Get current cookie status"""
    return {
        "loaded": session_cookies is not None,
        "keys": list(session_cookies.keys()) if session_cookies else []
    }


@app.websocket("/ws/generate-image")
async def websocket_generate_image(websocket: WebSocket):
    """
    WebSocket endpoint for real-time image generation
    
    Expected message format:
    {
        "prompt": "...",
        "aspect_ratio": "1:1",
        "quality": "standard"
    }
    """
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
            
            # Generate image via Grok client
            async with GrokClient(cookies=session_cookies) as client:
                async for progress in client.generate_image(
                    prompt=request.get("prompt", ""),
                    aspect_ratio=request.get("aspect_ratio", "1:1"),
                    quality=request.get("quality", "standard")
                ):
                    await websocket.send_text(progress)
    
    except Exception as e:
        try:
            await websocket.send_json({
                "status": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        await websocket.close()


@app.websocket("/ws/generate-video")
async def websocket_generate_video(websocket: WebSocket):
    """
    WebSocket endpoint for real-time video generation
    
    Expected message format:
    {
        "prompt": "...",
        "duration": 6,
        "aspect_ratio": "16:9",
        "resolution": "480p"
    }
    """
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
            
            # Generate video via Grok client
            async with GrokClient(cookies=session_cookies) as client:
                async for progress in client.generate_video(
                    prompt=request.get("prompt", ""),
                    duration=request.get("duration", 6),
                    aspect_ratio=request.get("aspect_ratio", "16:9"),
                    resolution=request.get("resolution", "480p")
                ):
                    await websocket.send_text(progress)
    
    except Exception as e:
        try:
            await websocket.send_json({
                "status": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        await websocket.close()


@app.post("/api/generate-image")
async def generate_image(request: GenerateImageRequest):
    """
    REST endpoint for image generation (non-streaming)
    """
    if not session_cookies:
        raise HTTPException(
            status_code=401,
            detail="No authentication cookies. Please set cookies first."
        )
    
    results = []
    async with GrokClient(cookies=session_cookies) as client:
        async for progress in client.generate_image(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality
        ):
            results.append(json.loads(progress))
    
    return {"results": results}


@app.post("/api/generate-video")
async def generate_video(request: GenerateVideoRequest):
    """
    REST endpoint for video generation (non-streaming)
    """
    if not session_cookies:
        raise HTTPException(
            status_code=401,
            detail="No authentication cookies. Please set cookies first."
        )
    
    results = []
    async with GrokClient(cookies=session_cookies) as client:
        async for progress in client.generate_video(
            prompt=request.prompt,
            duration=request.duration,
            aspect_ratio=request.aspect_ratio,
            resolution=request.resolution
        ):
            results.append(json.loads(progress))
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    
    # Create static directory if it doesn't exist
    static_dir.mkdir(exist_ok=True)
    
    print("Starting Grok Aurora Studio...")
    print("Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
