import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~")) / ".clipfusion" / "clipfusion.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                video_path TEXT NOT NULL,
                language TEXT DEFAULT 'pt',
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                full_text TEXT,
                segments_json TEXT,
                quality_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                transcript_id INTEGER NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                text TEXT NOT NULL,
                hook_strength REAL DEFAULT 0.0,
                retention_score REAL DEFAULT 0.0,
                moment_strength REAL DEFAULT 0.0,
                shareability REAL DEFAULT 0.0,
                platform_fit_tiktok REAL DEFAULT 0.0,
                platform_fit_reels REAL DEFAULT 0.0,
                platform_fit_shorts REAL DEFAULT 0.0,
                combined_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cuts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                candidate_id INTEGER,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                title TEXT,
                hook TEXT,
                archetype TEXT,
                platforms TEXT,
                protection_level TEXT DEFAULT 'none',
                output_paths TEXT,
                viral_score REAL DEFAULT 0.0,
                decision TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS performances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cut_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                posted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cut_id) REFERENCES cuts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                subkey TEXT,
                weight REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


def normalize_scores(payload: dict) -> dict:
    payload = dict(payload or {})
    # mapeamentos legados -> schema canônico
    if "retention_score" not in payload and "retencao_estimada" in payload:
        payload["retention_score"] = payload.get("retencao_estimada", 0.0)
    if "moment_strength" not in payload and "comentabilidade" in payload:
        payload["moment_strength"] = payload.get("comentabilidade", 0.0)
    return payload


def save_candidate(project_id, transcript_id, start, end, text, scores=None):
    s = normalize_scores(scores or {})
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO candidates (
                project_id, transcript_id, start_time, end_time, text,
                hook_strength, retention_score, moment_strength, shareability,
                platform_fit_tiktok, platform_fit_reels, platform_fit_shorts, combined_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id, transcript_id, start, end, text,
                float(s.get("hook", s.get("hook_strength", 0.0)) or 0.0),
                float(s.get("retention_score", 0.0) or 0.0),
                float(s.get("moment_strength", 0.0) or 0.0),
                float(s.get("shareability", 0.0) or 0.0),
                float(s.get("platform_fit_tiktok", 0.0) or 0.0),
                float(s.get("platform_fit_reels", 0.0) or 0.0),
                float(s.get("platform_fit_shorts", 0.0) or 0.0),
                float(s.get("combined", s.get("combined_score", 0.0)) or 0.0),
            ),
        )
        conn.commit()
        return cur.lastrowid


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False)


def from_json(raw, fallback):
    if not raw:
        return fallback
    return json.loads(raw)
