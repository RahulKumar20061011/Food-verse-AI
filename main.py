import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

load_dotenv()
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "food_verse.db"
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = FastAPI(title="Food Verse AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def init_db():
    """Create a small SQLite table to save the user's recent results."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                feature TEXT NOT NULL,
                user_input TEXT NOT NULL,
                result TEXT NOT NULL
            )
        """)
        conn.commit()


def save_history(feature: str, user_input: str, result: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO history (created_at, feature, user_input, result) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), feature, user_input[:1000], result[:15000]),
        )
        conn.commit()


def get_ai_response(prompt: str, image_bytes: Optional[bytes] = None, mime_type: str = "image/jpeg") -> str:
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API key not configured. Copy .env.example to .env and add your Gemini API key."
        )
    try:
        client = genai.Client(api_key=API_KEY)
        content = [prompt]
        if image_bytes is not None:
            content.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
        response = client.models.generate_content(model=MODEL, contents=content)
        answer = response.text
        if not answer:
            raise ValueError("The AI returned an empty response.")
        return answer
    except HTTPException:
        raise
    except Exception as exc:
        # Keep the API error readable for a student developer without exposing credentials.
        raise HTTPException(status_code=502, detail=f"AI service request failed: {exc}") from exc


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Food Verse AI", "model": MODEL, "api_key_configured": bool(API_KEY)}


@app.get("/api/history")
def history():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, created_at, feature, user_input, result FROM history ORDER BY id DESC LIMIT 12"
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/analyze-food")
async def analyze_food(image: UploadFile = File(...), mode: str = Form("nutrition")):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, or WEBP image.")
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 10 MB.")

    prompts = {
        "nutrition": """You are Food Verse AI's nutrition-estimation module.
Analyze the food shown. Identify likely foods, estimate a plausible portion, and give estimated calories,
protein, carbohydrates, fat, and fiber in a clear table. State assumptions and uncertainty prominently.
Image-based estimates are approximate, not laboratory measurements. Ask the user to provide portion weight
or ingredients for a better estimate. Do not provide medical diagnoses.""",
        "freshness": """You are Food Verse AI's food freshness assistant.
Describe only visible cues that may suggest freshness or deterioration, such as mold, bruising, discoloration,
or shriveling. Give cautious next steps. Never certify that food is safe from an image: pathogens and toxins
can be invisible, and appearance alone is insufficient. If there are concerning signs, advise discarding it
rather than tasting it. Avoid claiming certainty when evidence is unclear.""",
    }
    if mode not in prompts:
        raise HTTPException(status_code=400, detail="Unsupported image analysis mode.")
    result = get_ai_response(prompts[mode], data, image.content_type or "image/jpeg")
    save_history(mode, f"Uploaded image: {image.filename or 'food image'}", result)
    return {"feature": mode, "result": result}


@app.post("/api/recipes")
async def recipes(
    ingredients: str = Form(...),
    diet: str = Form("No preference"),
    time_limit: str = Form("30 minutes"),
    servings: str = Form("2"),
):
    if len(ingredients.strip()) < 2:
        raise HTTPException(status_code=400, detail="Please enter at least one ingredient.")
    prompt = f"""You are Food Verse AI's recipe assistant.
Ingredients available: {ingredients[:1500]}
Dietary preference: {diet[:100]}
Time available: {time_limit[:50]}
Servings: {servings[:10]}
Suggest two practical recipes. For each, provide a title, ingredients with approximate quantities,
step-by-step method, approximate preparation/cooking time, and substitutions.
Use clear beginner-friendly language. Flag common allergens when relevant. Do not assume the user has
ingredients they did not mention; label pantry staples as optional. Ask the user to verify allergens."""
    result = get_ai_response(prompt)
    save_history("recipes", f"Ingredients: {ingredients}; diet: {diet}", result)
    return {"result": result}


@app.post("/api/meal-plan")
async def meal_plan(
    days: str = Form("3"),
    diet: str = Form("Vegetarian"),
    budget: str = Form("Budget-friendly"),
    goal: str = Form("Balanced meals"),
    dislikes: str = Form("None provided"),
):
    if days not in {"1", "3", "7"}:
        raise HTTPException(status_code=400, detail="Choose 1, 3, or 7 days.")
    prompt = f"""You are Food Verse AI's meal-planning module.
Create a {days}-day meal plan.
Diet preference: {diet[:100]}
Budget: {budget[:100]}
Goal: {goal[:150]}
Foods to avoid/dislikes: {dislikes[:500]}
Provide a markdown table with breakfast, lunch, dinner, and one optional snack per day.
Then provide a concise shopping list grouped by food category and practical prep tips.
Use accessible ingredients and approximate portions. Do not promise weight loss or medical outcomes.
Nutrition estimates are approximate. Ask the user to verify allergies and adapt to personal medical needs."""
    result = get_ai_response(prompt)
    save_history("meal planner", f"{days} day(s); {diet}; {budget}; {goal}", result)
    return {"result": result}


@app.post("/api/ask")
async def ask(task: str = Form(...), preferences: str = Form("")):
    if len(task.strip()) < 2:
        raise HTTPException(status_code=400, detail="Please enter a question.")
    prompt = f"""You are Food Verse AI, a friendly food intelligence assistant.
User request: {task[:2000]}
Preferences/context: {preferences[:1000] or 'Not provided'}
Be practical and well structured. For recipes, include ingredients and numbered steps.
For nutrition, label estimates as approximate. Never guarantee food safety from an image or replace professional
medical advice. Respect stated dietary preferences and ask about important missing constraints."""
    result = get_ai_response(prompt)
    save_history("chat assistant", task, result)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
