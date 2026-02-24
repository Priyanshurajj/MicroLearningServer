"""
main.py - FastAPI application entry point for MicroLearningServer.

Endpoints:
    POST /upload          – Upload a .txt or .pdf file (triggers background pipeline)
    GET  /files           – List all uploaded files
    GET  /status/{file_id} – Get file status, script, and associated videos

Day 3: Refactored to use tasks.py pipeline, added /audio & /videos dirs,
       added static file serving for generated videos.

Run with:
    uvicorn main:app --reload
"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from database import init_db, insert_file, get_all_files, get_file_by_id, get_videos_by_file_id, update_file_status
from tasks import process_file

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MicroLearningServer",
    description="Backend API for the Micro-Learning Portal – handles file uploads, text extraction, AI script generation, TTS audio, video generation, and status tracking.",
    version="3.0.0",
)

# ---------------------------------------------------------------------------
# CORS – allow all origins for development convenience
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path("uploads")                     # Directory to store uploaded files
AUDIO_DIR = Path("audio")                        # Directory to store generated audio
VIDEOS_DIR = Path("videos")                      # Directory to store generated videos
ALLOWED_EXTENSIONS = {".txt", ".pdf"}            # Only these file types are accepted

# ---------------------------------------------------------------------------
# Startup event – initialize DB and create directories
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    """
    Runs once when the server starts.
    - Creates the uploads, audio, and videos directories if they don't exist.
    - Initializes the SQLite database tables.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[STARTUP] Upload directory ready: {UPLOAD_DIR.resolve()}", flush=True)
    print(f"[STARTUP] Audio directory ready:  {AUDIO_DIR.resolve()}", flush=True)
    print(f"[STARTUP] Videos directory ready: {VIDEOS_DIR.resolve()}", flush=True)
    init_db()
    print("[STARTUP] Server is ready.", flush=True)

# ---------------------------------------------------------------------------
# Static file serving – serve generated videos
# ---------------------------------------------------------------------------
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")


# ---------------------------------------------------------------------------
# POST /upload – Upload a .txt or .pdf file
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accept a .txt or .pdf file upload and trigger the full background pipeline.

    Pipeline (runs in background):
        1. Extract text from file
        2. Generate script via Gemini AI
        3. Generate TTS audio
        4. Generate video from slides + audio
        5. Update database with results
    """
    print(f"\n[UPLOAD] --- New upload request received: {file.filename} ---", flush=True)

    # --- Step 1: Validate file extension ---
    original_filename = file.filename or "unknown"
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        print(f"[UPLOAD] Invalid file extension: {file_extension}", flush=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_extension}'. Only .txt and .pdf files are allowed.",
        )

    # --- Step 2: Generate a unique filename ---
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    # --- Step 3: Save the file to disk ---
    file_path = UPLOAD_DIR / unique_filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    print(f"[UPLOAD] Saved file to disk: {file_path}", flush=True)

    # --- Step 4: Insert record into the database ---
    file_id = insert_file(
        filename=unique_filename,
        original_filename=original_filename,
    )
    print(f"[UPLOAD] DB record created: file_id={file_id}", flush=True)

    # --- Step 5: Set status to 'processing' and trigger background pipeline ---
    update_file_status(file_id, "processing")
    background_tasks.add_task(process_file, file_id, str(file_path), original_filename)
    print(f"[UPLOAD] Background pipeline queued for file_id={file_id}\n", flush=True)

    # --- Step 6: Return response immediately ---
    return {
        "file_id": file_id,
        "filename": original_filename,
        "status": "processing",
    }


# ---------------------------------------------------------------------------
# GET /files – List all uploaded files
# ---------------------------------------------------------------------------
@app.get("/files")
def list_files():
    """
    Return a list of all uploaded file records from the database.
    Results are ordered by most recent first.
    """
    files = get_all_files()
    return {"files": files}


# ---------------------------------------------------------------------------
# GET /status/{file_id} – Get file status + script + associated video status
# ---------------------------------------------------------------------------
@app.get("/status/{file_id}")
def file_status(file_id: int):
    """
    Return the status of a specific file, its generated script, and any associated videos.
    """
    # Look up the file record
    file_record = get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail=f"File with id {file_id} not found.",
        )

    # Look up any associated video records
    videos = get_videos_by_file_id(file_id)

    # Parse script_json back to dict if it exists
    script = None
    if file_record.get("script_json"):
        try:
            script = json.loads(file_record["script_json"])
        except json.JSONDecodeError:
            script = None

    return {
        "file_id": file_record["id"],
        "filename": file_record["original_filename"],
        "status": file_record["status"],
        "script": script,
        "created_at": file_record["created_at"],
        "videos": videos,
    }
