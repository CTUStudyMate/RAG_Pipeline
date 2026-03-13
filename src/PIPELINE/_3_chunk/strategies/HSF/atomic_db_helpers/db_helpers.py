import sqlite3
from pathlib import Path
from src.common_utils.filename_handle import normalize_filename
from datetime import datetime


def create_db_for_document(file_path: str):

    document_name = normalize_filename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    db_dir = Path("data/db")
    db_dir.mkdir(parents=True, exist_ok=True)

    db_path = db_dir / f"{document_name}_{timestamp}.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS atomic_elements (
        id TEXT PRIMARY KEY,

        type TEXT NOT NULL,              -- picture / section_header / paragraph / footer
        content TEXT,                    -- text hoặc base64 image
        token_count INTEGER,

        atomic_order INTEGER NOT NULL,   -- thứ tự trong tài liệu

        description TEXT,
        level INTEGER,                   -- cho heading
        heading_type TEXT,
        path TEXT,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_atomic_order
    ON atomic_elements(atomic_order);
    """)

    conn.commit()

    return conn


def insert_atomic_into_db(element, cursor):

    metadata = element.get("metadata", {})

    cursor.execute("""
        INSERT OR REPLACE INTO atomic_elements (
            id,
            type,
            content,
            token_count,
            atomic_order,
            description,
            level,
            heading_type,
            path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            element["id"],
            element["type"],
            element.get("content"),
            element.get("token_count"),
            metadata.get("atomic_order"),
            metadata.get("description"),
            metadata.get("level"),
            metadata.get("heading"),
            None
        ))
