"""
main.py - FastAPI application entry point for MicroLearningServer.

Endpoints:
    POST /upload          – Upload a .txt or .pdf file
    GET  /files           – List all uploaded files
    GET  /status/{file_id} – Get file status and associated videos

Run with:
    uvicorn main:app --reload
"""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db, insert_file, get_all_files, get_file_by_id, get_videos_by_file_id

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MicroLearningServer",
    description="Backend API for the Micro-Learning Portal – handles file uploads and video status tracking.",
    version="1.0.0",
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
    print(f"[STARTUP] Upload directory ready: {UPLOAD_DIR.resolve()}")
    init_db()
    print("[STARTUP] Server is ready.")


# ---------------------------------------------------------------------------
# POST /upload – Upload a .txt or .pdf file
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accept a .txt or .pdf file upload.

    Steps:
        1. Validate the file extension.
        2. Generate a unique filename using UUID (preserves original extension).
        3. Save the file to the uploads directory.
        4. Insert a record into the 'files' database table.
        5. Return file metadata.

    Raises:
        HTTPException 400 – If the file type is not .txt or .pdf.
    """
    # --- Step 1: Validate file extension ---
    original_filename = file.filename or "unknown"
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
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

    print(f"[UPLOAD] Saved file: {file_path}  (original: {original_filename})")

    # --- Step 4: Insert record into the database ---
    file_id = insert_file(
        filename=unique_filename,
        original_filename=original_filename,
    )

    # --- Step 5: Return response ---
    return {
        "file_id": file_id,
        "filename": original_filename,
        "status": "uploaded",
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
# GET /status/{file_id} – Get file status + associated video status
# ---------------------------------------------------------------------------
@app.get("/status/{file_id}")
def file_status(file_id: int):
    """
    Return the status of a specific file and any associated videos.

    Raises:
        HTTPException 404 – If no file with the given ID exists.
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

    return {
        "file_id": file_record["id"],
        "filename": file_record["original_filename"],
        "status": file_record["status"],
        "created_at": file_record["created_at"],
        "videos": videos,
    }
