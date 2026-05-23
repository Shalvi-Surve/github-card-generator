import os
import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.genai import types

from agent import github_card_agent

# ---------------- logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- app ----------------
app = FastAPI(title="GitHub Dev Card Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- folders ----------------
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")

os.makedirs(CARDS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------- request model ----------------
class GenerateRequest(BaseModel):
    username: str


# ---------------- GitHub check ----------------
async def check_github_user(username: str) -> bool:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    async with httpx.AsyncClient(headers=headers) as client:
        try:
            res = await client.get(f"https://api.github.com/users/{username}")
            return res.status_code == 200
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return False


# ---------------- generate route ----------------
@app.post("/generate")
async def generate(request: GenerateRequest):
    username = request.username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    user_key = username.lower()

    logger.info(f"Generating card for {username}")

    if not await check_github_user(username):
        raise HTTPException(status_code=404, detail="GitHub user not found")

    try:
        card_filename = f"{user_key}.html"
        card_path = os.path.join(CARDS_DIR, card_filename)

        html = f"""
        <html>
        <head><title>{username}</title></head>
        <body>
            <h1>GitHub Card for {username}</h1>
        </body>
        </html>
        """

        with open(card_path, "w", encoding="utf-8") as f:
            f.write(html)

        return {
            "status": "success",
            "username": username,
            "card_url": f"/static/cards/{card_filename}",
            "html": html
        }

    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- get card ----------------
@app.get("/card/{username}")
async def get_card(username: str):
    path = os.path.join(CARDS_DIR, f"{username}.html")

    if os.path.exists(path):
        return FileResponse(path)

    path = os.path.join(CARDS_DIR, f"{username.lower()}.html")

    if os.path.exists(path):
        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Card not found")


# ---------------- health ----------------
@app.get("/health")
async def health():
    return {"status": "ok"}