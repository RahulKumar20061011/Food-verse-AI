# Food Verse AI — Complete Student Project Starter

Food Verse AI is a multimodal food intelligence web app with:
1. Food-image nutrition estimates
2. Food freshness clues from visible appearance
3. Ingredient-based recipe suggestions
4. Personalized 1-, 3-, or 7-day meal planning
5. Recent-result history stored locally with SQLite

## Stack
- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python, FastAPI
- AI model API: Google Gemini (`google-genai`)
- Local history database: SQLite

## Requirements
- Python 3.10 or newer
- A Gemini API key
- Internet connection for AI requests
- VS Code recommended

## Run on macOS
Open this folder in VS Code. In Terminal, run these commands one at a time:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` in VS Code and replace the placeholder with your Gemini API key. Do not share it or upload it to GitHub.

Start the server:

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000` in Chrome.

Stop the server with `Control + C`.

## API routes
- `GET /` — frontend
- `GET /api/health` — backend status
- `GET /api/history` — latest saved results
- `POST /api/analyze-food` — image analysis; multipart fields `image`, `mode` (`nutrition` or `freshness`)
- `POST /api/recipes` — form fields `ingredients`, `diet`, `time_limit`, `servings`
- `POST /api/meal-plan` — form fields `days`, `diet`, `budget`, `goal`, `dislikes`
- `POST /api/ask` — general food question; fields `task`, optional `preferences`

## How the app works
1. A user submits a food image or text form in the browser.
2. JavaScript sends the form to a FastAPI endpoint.
3. Python validates input and builds a task-specific prompt.
4. The Gemini API generates a response.
5. The backend saves the result in SQLite and sends it back to the browser.
6. The UI displays the result and the History page can retrieve recent saved results.

## Suggested college-submission checklist
- [ ] Test every feature using several sample inputs.
- [ ] Capture screenshots of the dashboard and each module.
- [ ] Add a project report with problem statement, objectives, architecture, implementation, testing, limitations, and future scope.
- [ ] Add your own README screenshots after testing.
- [ ] Push code to GitHub only after checking that `.env` is excluded.
- [ ] Record a short demo showing the four features.

## Limitations and safety
- Nutrition estimates from images may be inaccurate because ingredients and portion sizes are uncertain.
- A photo cannot prove that food is safe; pathogens and toxins can be invisible.
- Allergy and dietary information must be checked by the user.
- This prototype is not a medical tool or commercial food-safety certification system.
- Add authentication, rate limits, production error handling, privacy controls, and HTTPS before public deployment.
