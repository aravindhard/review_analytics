import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("REVIEWS_DB_PATH", Path(__file__).parent / "reviews.db"))

def get_connection():
    """Create and return a new connection to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access to rows
    return conn

def init_db():
    """Create the reviews table if it doesn't already exist."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review TEXT NOT NULL,
                label TEXT NOT NULL,
                rating INTEGER NOT NULL,
                theme TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def insert_review(review: str, label: str, rating: int, theme: str):
    """Insert a new review record into the database."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO reviews (review, label, rating, theme)
            VALUES (?, ?, ?, ?)
            """,
            (review, label, rating, theme),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_reviews(reviews):
    """Insert multiple review records in one transaction."""
    conn = get_connection()
    try:
        conn.executemany(
            """
            INSERT INTO reviews (review, label, rating, theme)
            VALUES (?, ?, ?, ?)
            """,
            [
                (item["review"], item["label"], item["rating"], item.get("theme"))
                for item in reviews
            ],
        )
        conn.commit()
        return len(reviews)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_all_reviews():
    """Fetch all review records from the database."""
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM reviews")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
