"""
database.py - SQLite database setup and helper functions.

Uses Python's built-in sqlite3 module (no ORM).
Database file is stored as 'microlearning.db' in the project root.

Day 2: Added script_json column and update_file_status helper.
"""

import sqlite3
from datetime import datetime

# ---------------------------------------------------------------------------
# Database path
# ---------------------------------------------------------------------------
DATABASE_PATH = "microlearning.db"


def get_connection() -> sqlite3.Connection:
    """
    Create and return a new SQLite connection.
    Enables row_factory so query results behave like dictionaries.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


# ---------------------------------------------------------------------------
# Initialization – create tables if they don't exist
# ---------------------------------------------------------------------------
def init_db() -> None:
    """
    Initialize the database by creating the required tables.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Table: files – stores metadata about uploaded files
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            filename          TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'uploaded',
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table: videos – stores generated video metadata linked to a file
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

    # Day 2: Add script_json column if it doesn't already exist
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN script_json TEXT")
        print("[DB] Added 'script_json' column to files table.")
    except sqlite3.OperationalError:
        # Column already exists — safe to ignore
        pass

    conn.commit()
    conn.close()
    print("[DB] Database initialized – tables ready.")


# ---------------------------------------------------------------------------
# Helper functions – Files
# ---------------------------------------------------------------------------
def insert_file(filename: str, original_filename: str) -> int:
    """
    Insert a new file record with status 'uploaded'.
    Returns the newly created file ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (filename, original_filename, status, created_at) VALUES (?, ?, ?, ?)",
        (filename, original_filename, "uploaded", datetime.utcnow()),
    )
    conn.commit()
    file_id = cursor.lastrowid  # Auto-generated primary key
    conn.close()
    return file_id


def get_all_files() -> list[dict]:
    """
    Retrieve every record from the files table.
    Returns a list of dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    # Convert sqlite3.Row objects to plain dicts for JSON serialization
    return [dict(row) for row in rows]


def get_file_by_id(file_id: int) -> dict | None:
    """
    Retrieve a single file record by its ID.
    Returns a dictionary or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Helper functions – Videos
# ---------------------------------------------------------------------------
def get_videos_by_file_id(file_id: int) -> list[dict]:
    """
    Retrieve all video records associated with a given file ID.
    Returns a list of dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM videos WHERE file_id = ? ORDER BY created_at DESC",
        (file_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Helper functions – File status updates (Day 2)
# ---------------------------------------------------------------------------
def update_file_status(file_id: int, status: str, script_json: str | None = None) -> None:
    """
    Update the status (and optionally the script_json) of a file record.

    Args:
        file_id: The ID of the file to update.
        status: New status string (e.g. 'processing', 'script_ready', 'script_failed').
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
