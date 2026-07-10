import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import database


load_dotenv()
client = None
try:
    from google import genai
    from google.genai import types

    if os.getenv("GOOGLE_API_KEY"):
        client = genai.Client()
except Exception:
    genai = None
    types = None

database.init_db()  # ensures table exists when app starts

app = FastAPI()

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

@app.get("/")
def app_root():
    return "Hello Aravind It is working, good job!!"

@app.get("/getmodals")
def get_models():
    if client is None:
        return JSONResponse(status_code=500, content={"detail": "Google client is not configured."})

    models = []
    for model in client.models.list():
        models.append(model.name)

    return models

def fallback_analysis(text: str):
    lowered = text.lower()
    if any(word in lowered for word in ["bad", "poor", "terrible", "awful", "slow", "late", "broken"]):
        label = "poor"
        score = 1
    elif any(word in lowered for word in ["great", "good", "excellent", "amazing", "love", "fast", "friendly", "awesome"]):
        label = "good"
        score = 5
    else:
        label = "average"
        score = 3

    if any(word in lowered for word in ["delivery", "shipping", "arrived", "late"]):
        theme = "delivery"
    elif any(word in lowered for word in ["service", "staff", "helpful", "support"]):
        theme = "service"
    elif any(word in lowered for word in ["price", "cost", "cheap", "expensive"]):
        theme = "price"
    elif any(word in lowered for word in ["quality", "product", "packaging", "durable"]):
        theme = "quality"
    else:
        theme = "general"

    return Analysis(label=label, score=score, theme=theme)


def analyze_text(text: str):
    """Use Gemini when available and fall back locally if it cannot respond."""
    if client is not None and types is not None:
        try:
            prompt = f'''
                You are an assistant to review the review and provide me the rating in a format.
                Input review: {text}
                Response:
                label: poor/average/good
                score: 0 to 5 (low to high)
                theme: one word describing the main topic, e.g. delivery
            '''
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Analysis,
                ),
            )
            if response.parsed is not None:
                return response.parsed
        except Exception:
            # Uploads should remain usable if Gemini is unavailable, rate limited,
            # or configured with an unsupported model.
            pass

    return fallback_analysis(text)


@app.post("/analyze")
def analyze_reviews(review: Review):
    try:
        result = analyze_text(review.text)

        return {"review": review.text, "label": result.label, "score": result.score, "theme": result.theme}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error is : {e}"})


@app.get("/allReviews")
def get_all_reviews():
    try:
        result = database.get_all_reviews();
    except Exception as e:
        return f'Error is {e}'

    return result

@app.post("/postReview")
def post_review(review: WholeReview):
    try:
        database.insert_review(
            review=review.review,
            label=review.analysis.label,
            rating=review.analysis.score,
            theme=review.analysis.theme,
        )
        return {"message": "Review saved successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error is {e}"})


@app.post("/postReviews")
def post_reviews(payload: BulkReviews):
    """Save an uploaded batch atomically so partial imports cannot occur."""
    try:
        rows = [
            {
                "review": item.review,
                "label": item.analysis.label,
                "rating": item.analysis.score,
                "theme": item.analysis.theme,
            }
            for item in payload.reviews
        ]
        saved = database.insert_reviews(rows)
        return {"message": "Reviews saved successfully", "saved": saved}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error is {e}"})
