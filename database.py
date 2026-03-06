import sqlite3
from datetime import datetime

DATABASE_PATH = "microlearning.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            filename          TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'uploaded',
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL,
            video_path  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id)
        )
    """)

    try:
        cursor.execute("ALTER TABLE files ADD COLUMN script_json TEXT")
        print("[DB] Added 'script_json' column to files table.")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("[DB] Database initialized – tables ready.")

def insert_file(filename: str, original_filename: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (filename, original_filename, status, created_at) VALUES (?, ?, ?, ?)",
        (filename, original_filename, "uploaded", datetime.utcnow()),
    )
    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    return file_id


def get_all_files() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    # Convert sqlite3.Row objects to plain dicts for JSON serialization
    return [dict(row) for row in rows]


def get_file_by_id(file_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_videos_by_file_id(file_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM videos WHERE file_id = ? ORDER BY created_at DESC",
        (file_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_video(file_id: int, video_path: str, status: str = "ready") -> int:
    """
    Insert a new video record linked to a file.

    Args:
        file_id: The ID of the parent file record.
        video_path: Path to the generated video file on disk.
        status: Video status (default 'ready').

    Returns:
        The newly created video ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO videos (file_id, video_path, status, created_at) VALUES (?, ?, ?, ?)",
        (file_id, video_path, status, datetime.utcnow()),
    )
    conn.commit()
    video_id = cursor.lastrowid
    conn.close()
    print(f"[DB] Video record created: id={video_id}, file_id={file_id}, status='{status}'.")
    return video_id


def update_file_status(file_id: int, status: str, script_json: str | None = None) -> None:
    """
    Update the status (and optionally the script_json) of a file record.

    Args:
        file_id: The ID of the file to update.
        status: New status string (e.g. 'processing', 'script_ready', 'video_ready', 'failed').
        script_json: Optional JSON string of the generated script.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if script_json is not None:
        cursor.execute(
            "UPDATE files SET status = ?, script_json = ? WHERE id = ?",
            (status, script_json, file_id),
        )
    else:
        cursor.execute(
            "UPDATE files SET status = ? WHERE id = ?",
            (status, file_id),
        )

    conn.commit()
    conn.close()
    print(f"[DB] File {file_id} status updated to '{status}'.")
