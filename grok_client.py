"""
Grok Aurora API Client
Handles image and video generation requests via Grok's REST API
"""

import aiohttp
import json
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime


class GrokClient:
    """Client for Grok Aurora image and video generation"""
    
    BASE_URL = "https://grok.com/rest"
    
    def __init__(self, cookies: Optional[dict] = None):
        """
        Initialize Grok client
        
        Args:
            cookies: Browser cookies dict (sso, cf_clearance, etc.)
        """
        self.cookies = cookies or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(cookies=self.cookies)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        quality: str = "standard"
    ) -> AsyncGenerator[str, None]:
        """
        Generate image using Grok Aurora
        
        Args:
            prompt: Image generation prompt
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, etc.)
            quality: Quality level (standard, high)
        
        Yields:
            JSON strings with generation progress/results
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        # Create conversation for image generation
        payload = {
            "temporary": True,
            "modelName": "imagine-image-gen",
            "message": f"{prompt}",
            "responseMetadata": {
                "modelConfigOverride": {
                    "modelMap": {
                        "imageGenModelConfig": {
                            "aspectRatio": aspect_ratio,
                            "quality": quality
                        }
                    }
                }
            }
        }
        
        try:
            async with self.session.post(
                f"{self.BASE_URL}/app-chat/conversations/new",
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield json.dumps({
                        "status": "error",
                        "code": resp.status,
                        "message": error_text[:200]
                    })
                    return
                
                # Stream SSE response
                async for line in resp.content:
                    if line:
                        text = line.decode('utf-8').strip()
                        if text.startswith('data: '):
                            data_str = text[6:]
                            try:
                                data = json.loads(data_str)
                                yield json.dumps({
                                    "status": "generating",
                                    "data": data
                                })
                            except json.JSONDecodeError:
                                pass
        except asyncio.TimeoutError:
            yield json.dumps({
                "status": "error",
                "message": "Generation timeout"
            })
        except Exception as e:
            yield json.dumps({
                "status": "error",
                "message": str(e)
            })
    
    async def generate_video(
        self,
        prompt: str,
        duration: int = 6,
        aspect_ratio: str = "16:9",
        resolution: str = "480p"
    ) -> AsyncGenerator[str, None]:
        """
        Generate video using Grok Aurora
        
        Args:
            prompt: Video generation prompt
            duration: Video duration in seconds (6, 12)
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            resolution: Video resolution (480p, 720p)
        
        Yields:
            JSON strings with generation progress/results
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        # Create conversation for video generation
        payload = {
            "temporary": True,
            "modelName": "imagine-video-gen",
            "message": f"{prompt} --mode=custom",
            "responseMetadata": {
                "modelConfigOverride": {
                    "modelMap": {
                        "videoGenModelConfig": {
                            "aspectRatio": aspect_ratio,
                            "videoLength": duration,
                            "resolutionName": resolution,
                            "isVideoEdit": False
                        }
                    }
                }
            }
        }
        
        try:
            async with self.session.post(
                f"{self.BASE_URL}/app-chat/conversations/new",
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield json.dumps({
                        "status": "error",
                        "code": resp.status,
                        "message": error_text[:200]
                    })
                    return
                
                # Stream SSE response
                async for line in resp.content:
                    if line:
                        text = line.decode('utf-8').strip()
                        if text.startswith('data: '):
                            data_str = text[6:]
                            try:
                                data = json.loads(data_str)
                                yield json.dumps({
                                    "status": "generating",
                                    "data": data
                                })
                            except json.JSONDecodeError:
                                pass
        except asyncio.TimeoutError:
            yield json.dumps({
                "status": "error",
                "message": "Video generation timeout"
            })
        except Exception as e:
            yield json.dumps({
                "status": "error",
                "message": str(e)
            })
    
    async def get_post(self, post_id: str) -> dict:
        """
        Get post details (image/video result)
        
        Args:
            post_id: Post ID from generation response
        
        Returns:
            Post data including media URLs
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        try:
            async with self.session.post(
                f"{self.BASE_URL}/media/post/get",
                json={"postId": post_id},
                headers=self.headers
            ) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}
