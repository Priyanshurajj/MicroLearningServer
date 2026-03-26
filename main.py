import logging
import os

from dotenv import load_dotenv

# Load env FIRST — agents/config.py reads env vars at import time
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import generate_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="EduReel ADK Server",
    description=(
        "Educational reel video generation server powered by Google ADK + Vertex AI. "
        "Submit transcript text and get an AI-generated educational reel video "
        "via a multi-agent pipeline."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "vertex_project": os.getenv("GOOGLE_CLOUD_PROJECT", "not set"),
        "vertex_location": os.getenv("GOOGLE_CLOUD_LOCATION", "not set"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
