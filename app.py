import streamlit as st
import requests
import pandas as pd

from frontend_utils import find_review_column, parse_reviews, rating_summary, read_review_file

BACKEND_URL = "http://127.0.0.1:8000"


def backend_error(response):
    """Return the backend's useful error detail instead of only its HTTP status."""
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

st.set_page_config(page_title="Review Analytics Dashboard", page_icon="📊", layout="wide")

st.title("Review Analytics Dashboard")
st.caption("Paste reviews or import a CSV/Excel file, analyze every record, and save it to the local database.")

if "results" not in st.session_state:
    st.session_state.results = []

with st.sidebar:
    st.header("Controls")
    if st.button("Refresh saved reviews"):
        st.session_state.results = []

st.subheader("Import reviews from a file")
uploaded_file = st.file_uploader(
    "Upload CSV or Excel",
    type=["csv", "xlsx"],
    help="The file must contain a column with the customer review text.",
)

if uploaded_file is not None:
    try:
        uploaded_records = read_review_file(uploaded_file.getvalue(), uploaded_file.name)
        if not uploaded_records:
            st.warning("The uploaded file does not contain any records.")
        else:
            columns = list(uploaded_records[0].keys())
            detected_column = find_review_column(columns)
            default_index = columns.index(detected_column) if detected_column in columns else 0
            review_column = st.selectbox(
                "Column containing review text",
                columns,
                index=default_index,
            )
            st.caption(f"{len(uploaded_records)} record(s) found. All non-empty reviews will be analyzed and saved.")
            st.dataframe(uploaded_records[:10], use_container_width=True)

            if st.button("Analyze and store file", type="primary", use_container_width=True):
                review_values = [
                    str(row.get(review_column, "")).strip()
                    for row in uploaded_records
                    if pd.notna(row.get(review_column)) and str(row.get(review_column, "")).strip()
                ]
                if not review_values:
                    st.warning("The selected column does not contain any review text.")
                else:
                    progress = st.progress(0, text="Analyzing uploaded reviews...")
                    analysis_results = []
                    try:
                        for index, review in enumerate(review_values, start=1):
                            response = requests.post(
                                f"{BACKEND_URL}/analyze",
                                json={"text": review},
                                timeout=60,
                            )
                            if not response.ok:
                                raise requests.HTTPError(backend_error(response), response=response)
                            response.raise_for_status()
                            analysis_results.append(response.json())
                            progress.progress(index / len(review_values), text=f"Analyzed {index} of {len(review_values)}")

                        payload = {
                            "reviews": [
                                {
                                    "review": result["review"],
                                    "analysis": {
                                        "label": result["label"],
                                        "score": result["score"],
                                        "theme": result["theme"],
                                    },
                                }
                                for result in analysis_results
                            ]
                        }
                        response = requests.post(f"{BACKEND_URL}/postReviews", json=payload, timeout=60)
                        if not response.ok:
                            raise requests.HTTPError(backend_error(response), response=response)
                        response.raise_for_status()
                        st.session_state.results = analysis_results
                        progress.empty()
                        st.success(f"Analyzed and saved all {len(analysis_results)} review(s).")
                    except (requests.RequestException, KeyError) as exc:
                        progress.empty()
                        st.error(f"The file could not be imported. No partial batch was saved: {exc}")
    except (ValueError, ImportError, OSError, UnicodeError) as exc:
        st.error(f"Unable to read the uploaded file: {exc}")

st.divider()
st.subheader("Enter reviews manually")

review_text = st.text_area(
    "Paste customer reviews (one per line)",
    height=220,
    placeholder="Great service\nDelayed delivery\nVery friendly staff",
)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Analyze", use_container_width=True):
        reviews = parse_reviews(review_text)
        if not reviews:
            st.warning("Please enter at least one review before analyzing.")
            st.stop()

        analysis_results = []
        for review in reviews:
            try:
                response = requests.post(
                    f"{BACKEND_URL}/analyze",
                    json={"text": review},
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()
                analysis_results.append(result)
            except requests.RequestException as exc:
                st.error(f"Failed to analyze review: {exc}")
                analysis_results = []
                break

        if analysis_results:
            st.session_state.results = analysis_results
            st.success("Analysis complete.")

with col2:
    if st.button("Upload review(s)", use_container_width=True):
        if not st.session_state.results:
            st.warning("Analyze some reviews first so there is data to save.")
        else:
            saved = 0
            for result in st.session_state.results:
                try:
                    payload = {
                        "review": result.get("review") if isinstance(result, dict) and "review" in result else None,
                        "analysis": {
                            "label": result.get("label"),
                            "score": result.get("score"),
                            "theme": result.get("theme"),
                        },
                    }
                    response = requests.post(f"{BACKEND_URL}/postReview", json=payload, timeout=60)
                    response.raise_for_status()
                    saved += 1
                except requests.RequestException as exc:
                    st.error(f"Failed to save a review: {exc}")
                    break
            if saved:
                st.success(f"Saved {saved} review(s) to the database.")

if st.button("Load all saved reviews", use_container_width=True):
    try:
        response = requests.get(f"{BACKEND_URL}/allReviews", timeout=60)
        response.raise_for_status()
        saved_reviews = response.json()
        st.session_state.results = saved_reviews
        st.success(f"Loaded {len(saved_reviews)} saved review(s).")
    except requests.RequestException as exc:
        st.error(f"Unable to load saved reviews: {exc}")

if st.session_state.results:
    st.subheader("Rating analytics")
    summary = rating_summary(st.session_state.results)
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Total reviews", f"{summary['total']:,}")
    metric2.metric("Average rating", f"{summary['average']:.2f} / 5")
    metric3.metric("Positive ratings (4–5)", f"{summary['positive_percentage']:.1f}%")

    display_rows = []
    for item in st.session_state.results:
        if isinstance(item, dict):
            if "rating" in item and "score" not in item:
                item = {**item, "score": item.get("rating")}
            display_rows.append(
                {
                    "review": item.get("review"),
                    "label": item.get("label"),
                    "score": item.get("score"),
                    "theme": item.get("theme"),
                }
            )

    rating_counts = pd.DataFrame(display_rows)["score"].value_counts().reindex(range(0, 6), fill_value=0)
    rating_counts.index.name = "Rating"
    rating_counts.name = "Reviews"
    st.bar_chart(rating_counts)

    st.subheader("Latest results")
    st.dataframe(display_rows, use_container_width=True)
