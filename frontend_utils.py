from io import BytesIO

import pandas as pd


def parse_reviews(raw_text: str):
    """Split pasted review text into non-empty review strings."""
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def read_review_file(file_bytes: bytes, filename: str):
    """Read a CSV/XLSX file and return its non-empty records."""
    extension = filename.lower().rsplit(".", 1)[-1]
    source = BytesIO(file_bytes)
    if extension == "csv":
        frame = pd.read_csv(source)
    elif extension == "xlsx":
        frame = pd.read_excel(source)
    else:
        raise ValueError("Only .csv and .xlsx files are supported.")

    frame = frame.dropna(how="all")
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame.to_dict(orient="records")


def find_review_column(columns):
    """Choose the most likely review-text column from a spreadsheet."""
    aliases = {"review", "reviews", "text", "comment", "comments", "feedback", "review_text"}
    for column in columns:
        normalized = str(column).strip().lower().replace(" ", "_")
        if normalized in aliases:
            return column
    return None


def rating_summary(records):
    """Return total records, average rating, and positive-rating percentage."""
    ratings = []
    for record in records:
        value = record.get("rating", record.get("score")) if isinstance(record, dict) else None
        try:
            ratings.append(float(value))
        except (TypeError, ValueError):
            continue

    total = len(records)
    average = sum(ratings) / len(ratings) if ratings else 0.0
    positive = (sum(rating >= 4 for rating in ratings) / len(ratings) * 100) if ratings else 0.0
    return {"total": total, "average": average, "positive_percentage": positive}
