# Review Analytics Dashboard

A local review-analysis application built with Streamlit, FastAPI, SQLite, and optional Google Gemini analysis. Users can paste reviews manually or upload CSV/XLSX files, analyze every review, store the results, and view rating analytics.

## Features

- Paste and analyze multiple reviews, one per line.
- Upload `.csv` and `.xlsx` files containing review text.
- Automatically detect common review column names such as `review`, `text`, `comment`, and `feedback`.
- Preview uploaded records and manually select the review column.
- Analyze reviews with Gemini when configured.
- Fall back to a local keyword analyzer if Gemini is unavailable, rate-limited, or not configured.
- Store individual reviews or complete uploaded batches in SQLite.
- Save file imports transactionally so a failed insert does not create a partial batch.
- Display total reviews, average rating, positive-rating percentage, and a rating distribution chart.

## Architecture

```text
CSV/XLSX or pasted text
          |
          v
Streamlit frontend (app.py)
          |
          v
FastAPI backend (api.py)
     |              |
     v              v
Gemini/local     SQLite
analysis         reviews.db
```

## Project structure

```text
.
├── app.py                  # Streamlit user interface
├── api.py                  # FastAPI endpoints and review analysis
├── database.py             # SQLite schema and database operations
├── frontend_utils.py       # File parsing and analytics helpers
├── dummy_reviews.csv       # Ten sample reviews for testing uploads
├── tests/
│   ├── test_api.py
│   └── test_frontend_utils.py
├── pyproject.toml          # Project metadata and uv dependencies
├── requirements.txt        # pip-compatible dependencies
├── uv.lock                 # Reproducible uv dependency lockfile
└── context.md              # Reusable context for AI coding agents
```

## Requirements

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/) recommended for dependency management

Gemini is optional. Without a Google API key, the application uses its built-in local analyzer.

## Setup with uv

Clone the repository and enter the project directory:

```bash
git clone https://github.com/aravindhard/review_analytics.git
cd review_analytics
```

Install the locked dependencies:

```bash
uv sync
```

Optional: create a `.env` file to enable Gemini analysis:

```env
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Do not commit `.env`; it is already excluded by `.gitignore`.

## Setup with pip

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Run the application

The API and frontend are separate processes. Run them in two terminals.

Terminal 1 — start FastAPI:

```bash
uv run uvicorn api:app --reload --port 8000
```

Terminal 2 — start Streamlit:

```bash
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). FastAPI documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

If using the pip environment instead of uv, remove `uv run` from both commands.

## Upload a review file

1. Open the Streamlit dashboard.
2. Choose `dummy_reviews.csv` or another `.csv`/`.xlsx` file.
3. Select the column containing the review text. A column named `review` is detected automatically.
4. Select **Analyze and store file**.
5. Wait for every record to be analyzed and saved.

The minimum CSV format is:

```csv
review
Great service and fast delivery
The product was average
The package arrived late and damaged
```

Blank rows and blank review values are ignored. Other columns may be present and are shown in the upload preview, but only the selected review-text column is analyzed and stored.

## Analytics

The dashboard displays:

- **Total reviews**: number of currently loaded result records.
- **Average rating**: mean score on the 0–5 scale.
- **Positive ratings**: percentage of ratings greater than or equal to 4.
- **Rating distribution**: number of reviews at each score from 0 through 5.

Use **Load all saved reviews** to calculate the dashboard from all records currently stored in SQLite.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Backend health response |
| `POST` | `/analyze` | Analyze one review |
| `POST` | `/postReview` | Store one analyzed review |
| `POST` | `/postReviews` | Store a batch in one transaction |
| `GET` | `/allReviews` | Retrieve all stored reviews |
| `GET` | `/getmodals` | List Gemini models when configured |

Example analysis request:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Great service and fast delivery"}'
```

Example response:

```json
{
  "review": "Great service and fast delivery",
  "label": "good",
  "score": 5,
  "theme": "delivery"
}
```

## Database

SQLite creates `reviews.db` automatically when the API starts. The database is intentionally ignored by Git because it can contain local uploaded data.

The `reviews` table contains:

| Column | Type | Description |
| --- | --- | --- |
| `id` | INTEGER | Auto-incrementing primary key |
| `review` | TEXT | Original review text |
| `label` | TEXT | `poor`, `average`, or `good` |
| `rating` | INTEGER | Score from 0 through 5 |
| `theme` | TEXT | Main review topic |

Set `REVIEWS_DB_PATH` to use a different database location:

```bash
REVIEWS_DB_PATH=/path/to/reviews.db uv run uvicorn api:app --reload --port 8000
```

## Tests

Run the complete test suite:

```bash
uv run python -m unittest discover -s tests -v
```

The tests cover pasted-text parsing, CSV parsing, XLSX parsing, review-column detection, rating calculations, and fallback behavior when Gemini fails.

## Troubleshooting

### Streamlit reports that it cannot connect to port 8000

Start the FastAPI backend in a separate terminal:

```bash
uv run uvicorn api:app --reload --port 8000
```

### `/analyze` returns an error after changing API settings

Restart FastAPI so it reloads `.env`. If Gemini cannot respond, the application automatically uses the local analyzer.

### Excel files cannot be read

Install or synchronize dependencies so `openpyxl` is available:

```bash
uv sync
```

### Port 8501 is already in use

Start Streamlit on another port:

```bash
uv run streamlit run app.py --server.port 8502
```
