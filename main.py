import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from database import init_db, insert_file, get_all_files, get_file_by_id, get_videos_by_file_id, update_file_status
from tasks import process_file

load_dotenv()
app = FastAPI(
    title="MicroLearningServer",
    description="Backend API for the Micro-Learning Portal",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")                
AUDIO_DIR = Path("audio")              
VIDEOS_DIR = Path("videos")            
ALLOWED_EXTENSIONS = {".txt", ".pdf"} 

@app.on_event("startup")
def on_startup():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[STARTUP] Upload directory ready: {UPLOAD_DIR.resolve()}", flush=True)
    print(f"[STARTUP] Audio directory ready:  {AUDIO_DIR.resolve()}", flush=True)
    print(f"[STARTUP] Videos directory ready: {VIDEOS_DIR.resolve()}", flush=True)
    init_db()
    print("[STARTUP] Server is ready.", flush=True)

VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    print(f"\n[UPLOAD] --- New upload request received: {file.filename} ---", flush=True)

    original_filename = file.filename or "unknown"
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        print(f"[UPLOAD] Invalid file extension: {file_extension}", flush=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_extension}'. Only .txt and .pdf files are allowed.",
        )

    unique_filename = f"{uuid.uuid4().hex}{file_extension}"

    file_path = UPLOAD_DIR / unique_filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    print(f"[UPLOAD] Saved file to disk: {file_path}", flush=True)

    file_id = insert_file(
        filename=unique_filename,
        original_filename=original_filename,
    )
    print(f"[UPLOAD] DB record created: file_id={file_id}", flush=True)

    update_file_status(file_id, "processing")
    background_tasks.add_task(process_file, file_id, str(file_path), original_filename)
    print(f"[UPLOAD] Background pipeline queued for file_id={file_id}\n", flush=True)

    return {
        "file_id": file_id,
        "filename": original_filename,
        "status": "processing",
    }

@app.get("/files")
def list_files():
    files = get_all_files()
    return {"files": files}

@app.get("/status/{file_id}")
def file_status(file_id: int):
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
