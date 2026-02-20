"""
main.py - FastAPI application entry point for MicroLearningServer.

Endpoints:
    POST /upload          – Upload a .txt or .pdf file (triggers background processing)
    GET  /files           – List all uploaded files
    GET  /status/{file_id} – Get file status, script, and associated videos

Run with:
    uvicorn main:app --reload
"""

import os
import json
import uuid
import asyncio
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db, insert_file, get_all_files, get_file_by_id, get_videos_by_file_id, update_file_status
from text_extractor import extract_text
from gemini_service import generate_script

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MicroLearningServer",
    description="Backend API for the Micro-Learning Portal – handles file uploads, text extraction, AI script generation, and video status tracking.",
    version="2.0.0",
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
ALLOWED_EXTENSIONS = {".txt", ".pdf"}            # Only these file types are accepted

# ---------------------------------------------------------------------------
# Startup event – initialize DB and create upload directory
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    """
    Runs once when the server starts.
    - Creates the uploads directory if it doesn't exist.
    - Initializes the SQLite database tables.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[STARTUP] Upload directory ready: {UPLOAD_DIR.resolve()}", flush=True)
    init_db()
    print("[STARTUP] Server is ready.", flush=True)


# ---------------------------------------------------------------------------
# Background task – extract text and generate script
# ---------------------------------------------------------------------------
def process_file_sync(file_id: int, filepath: str):
    """
    Synchronous wrapper for the background task to ensure execution in threadpool.
    """
    print(f"[BACKGROUND] process_file_sync STARTED for file {file_id}: {filepath}", flush=True)
    try:
        # Step 1: Extract text
        print(f"[BACKGROUND] Extracting text for file {file_id}...", flush=True)
        text = extract_text(filepath)
        if not text or not text.strip():
            print(f"[BACKGROUND] No text extracted from file {file_id}.", flush=True)
            update_file_status(file_id, "script_failed")
            return

        print(f"[BACKGROUND] Extracted {len(text)} characters from file {file_id}. Sending to Gemini...", flush=True)

        # Step 2: Generate script using Gemini
        script = generate_script(text)

        if script:
            # Step 3a: Success – store the script as JSON
            script_json_str = json.dumps(script, ensure_ascii=False)
            update_file_status(file_id, "script_ready", script_json=script_json_str)
            print(f"[BACKGROUND] Script generated and saved successfully for file {file_id}!", flush=True)
        else:
            # Step 3b: Failure – mark as failed
            update_file_status(file_id, "script_failed")
            print(f"[BACKGROUND] Script generation returned None for file {file_id}.", flush=True)

    except Exception as e:
        print(f"[BACKGROUND] ERROR processing file {file_id}: {e}", flush=True)
        update_file_status(file_id, "script_failed")
        import traceback
        traceback.print_exc()
        
    print(f"[BACKGROUND] process_file_sync FINISHED for file {file_id}", flush=True)


# ---------------------------------------------------------------------------
# POST /upload – Upload a .txt or .pdf file
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accept a .txt or .pdf file upload and trigger background processing.
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
    print(f"[UPLOAD] Saved initial DB record with file_id: {file_id}. Status is currently 'uploaded'.", flush=True)

    # --- Step 5: Set status to 'processing' and trigger background task ---
    print(f"[UPLOAD] Updating status to 'processing' for file_id {file_id}...", flush=True)
    update_file_status(file_id, "processing")
    
    print(f"[UPLOAD] Queueing background task for file_id {file_id}...", flush=True)
    background_tasks.add_task(process_file_sync, file_id, str(file_path))

    # --- Step 6: Return response immediately ---
    print(f"[UPLOAD] Returning success response to client for file_id {file_id}...\n", flush=True)
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
