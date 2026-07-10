# Review Analytics Agent Context

Use this context to build or extend a local review-analytics application with a Streamlit frontend, FastAPI backend, SQLite persistence, CSV/XLSX imports, optional LLM analysis, and offline fallback behavior.

## Target outcome

Build an application that lets a user:

1. Paste one or more customer reviews.
2. Upload a CSV or XLSX file and select its review-text column.
3. Analyze every non-empty review into `label`, `score`, and `theme`.
4. Store individual reviews or an entire file batch in SQLite.
5. View total reviews, average rating, positive-rating percentage, a rating distribution, and the underlying records.

## Preferred stack

- Python 3.12+
- Streamlit for the frontend
- FastAPI and Pydantic for the backend
- SQLite for local persistence
- pandas and openpyxl for CSV/XLSX ingestion
- requests for frontend-to-backend calls
- Google Gemini as an optional analyzer
- `unittest` for automated tests
- uv for dependency locking and execution

Keep the frontend and API as separate processes. Default to `http://127.0.0.1:8000` for the API and port `8501` for Streamlit.

## Components

Implement these responsibilities separately:

- `app.py`: render the UI, call the API, show progress/errors, and visualize results.
- `api.py`: validate payloads, run analysis, expose single/bulk persistence endpoints.
- `database.py`: own the SQLite schema and all database transactions.
- `frontend_utils.py`: parse pasted text and spreadsheet files, detect columns, and calculate summaries.
- `tests/`: test pure helpers and analyzer fallback behavior.

Do not put database writes directly in Streamlit. Route persistence through FastAPI.

## Data contract

Represent an analyzed review as:

```json
{
  "review": "Great service and fast delivery",
  "label": "good",
  "score": 5,
  "theme": "delivery"
}
```

Use these Pydantic concepts:

```python
class Review(BaseModel):
    text: str

class Analysis(BaseModel):
    label: str
    score: int
    theme: str

class WholeReview(BaseModel):
    review: str
    analysis: Analysis

class BulkReviews(BaseModel):
    reviews: list[WholeReview]
```

Keep the database column named `rating`, while API analysis responses use `score`. Normalize this difference before displaying or saving records.

## Database schema

Create the table automatically when the API starts:

```sql
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review TEXT NOT NULL,
    label TEXT NOT NULL,
    rating INTEGER NOT NULL,
    theme TEXT
);
```

Implement both single-row insertion and `executemany` batch insertion. Wrap a batch in one transaction and roll it back on any failure. Never report a batch as saved unless the transaction commits.

Use `REVIEWS_DB_PATH` as an optional environment override. Default to `reviews.db` beside the source files. Exclude the database and `.env` from Git.

## Analysis behavior

Return:

- `label`: `poor`, `average`, or `good`
- `score`: integer from 0 through 5
- `theme`: short main topic such as `delivery`, `service`, `price`, `quality`, or `general`

If `GOOGLE_API_KEY` exists, attempt structured Gemini output using the `Analysis` Pydantic schema. Read the model from `GEMINI_MODEL` and provide a sensible default.

Gemini must be optional. Catch provider errors, invalid model errors, missing parsed responses, quota failures, and network failures, then run a deterministic local keyword analyzer. An external AI failure must not make file uploads unusable.

Local analysis may use keyword groups. Check negative language before positive language, assign a reasonable rating, and derive the theme independently.

## File-import workflow

Accept only `.csv` and `.xlsx` files. Read bytes through an in-memory buffer, remove completely empty rows, and strip column names.

Auto-detect these review-column aliases case-insensitively:

```text
review, reviews, text, comment, comments, feedback, review_text
```

Always let the user override the detected column. Show a preview and total row count before import.

On import:

1. Ignore null and blank review values.
2. Call `/analyze` for every remaining review.
3. Show progress during analysis.
4. Build one `/postReviews` request only after every review is analyzed.
5. Save the batch transactionally.
6. Show backend error details rather than only `500 Internal Server Error`.
7. Put analyzed records into session state so analytics appear immediately.

Avoid saving each file row independently because that can leave partial imports.

## Required API routes

- `POST /analyze`: accept `{"text": "..."}` and return the analyzed review.
- `POST /postReview`: store one analyzed review.
- `POST /postReviews`: store an analyzed batch atomically and return the saved count.
- `GET /allReviews`: return every stored review.
- `GET /`: provide a simple health response.

FastAPI automatically provides interactive documentation at `/docs`.

## Dashboard behavior

Keep results in Streamlit session state. Support manual analysis, saving analyzed manual reviews, importing files, and loading all stored reviews.

Show at least these three metrics:

- Total reviews: length of the loaded records.
- Average rating: mean of numeric `rating` or `score` values.
- Positive percentage: percentage of numeric ratings greater than or equal to 4.

Also show a bar chart with counts for ratings 0 through 5 and a table containing review, label, score, and theme.

Handle empty and malformed values without dividing by zero or crashing the dashboard.

## Error handling

- Use request timeouts for every frontend API call.
- Display the backend's JSON `detail` when available.
- Distinguish unreadable files from backend failures.
- Do not expose API keys or secrets in responses or logs.
- Keep the local analyzer operational when no external credentials exist.
- Explain that Streamlit and FastAPI must run concurrently when connection errors occur.

## Verification

Add tests for:

- Splitting non-empty pasted review lines.
- Reading a real CSV byte stream.
- Reading a real XLSX byte stream.
- Detecting common review-column aliases.
- Rating summary calculations.
- Falling back locally when the external analyzer raises an exception.

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Perform an end-to-end API check against a temporary database:

1. Start FastAPI with `REVIEWS_DB_PATH` pointing into a temporary directory.
2. Confirm `/analyze` returns HTTP 200.
3. Confirm `/postReviews` reports the correct saved count.
4. Confirm `/allReviews` returns the saved records.
5. Stop the temporary server.

Do not use or modify a user's existing `reviews.db` during integration tests.

## Completion checklist

- Both manual and file-based review input work.
- CSV and XLSX uploads work with selectable columns.
- Gemini configuration is optional.
- External analysis failures fall back locally.
- File batches save atomically.
- All three metrics and the rating chart render.
- Stored records can be reloaded.
- Tests pass.
- `.env`, virtual environments, cache files, and `reviews.db` are ignored by Git.
- README setup commands start both required processes.
