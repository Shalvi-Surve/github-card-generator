import os
import logging
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent import github_card_agent
from google.genai import types

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- FastAPI App ----------------
app = FastAPI(title="GitHub Dev Card Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Static Files ----------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")

os.makedirs(CARDS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------- Request Model ----------------
class GenerateRequest(BaseModel):
    username: str


# ---------------- GitHub Check ----------------
async def check_github_user(username: str) -> bool:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    async with httpx.AsyncClient(headers=headers) as client:
        try:
            res = await client.get(f"https://api.github.com/users/{username}")
            return res.status_code == 200
        except Exception as e:
            logger.error(f"GitHub check failed for {username}: {e}")
            return False


# ---------------- Generate Endpoint ----------------
@app.post("/generate")
async def generate(request: GenerateRequest):

    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    user_key = username.lower()

    logger.info(f"Request received for {username}")

    # Validate GitHub user
    if not await check_github_user(username):
        raise HTTPException(
            status_code=404,
            detail=f"GitHub user '{username}' not found"
        )

    try:
        # Fake agent call (you can replace later)
        content = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate a dev card for {username}")]
        )

        logger.info(f"Generating card for {username}")

        # ---------------- Create HTML Card ----------------
        card_filename = f"{user_key}.html"
        card_path = os.path.join(CARDS_DIR, card_filename)

        with open(card_path, "w", encoding="utf-8") as f:
            f.write(f"""
            <html>
                <body style="font-family: Arial;">
                    <h1>GitHub Card</h1>
                    <p>User: {username}</p>
                </body>
            </html>
            """)

        # Verify file
        if not os.path.exists(card_path):
            raise HTTPException(
                status_code=500,
                detail="Card file was not created"
            )

        with open(card_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        return {
            "status": "success",
            "username": username,
            "card_url": f"/static/cards/{card_filename}",
            "html": html_content
        }

    except Exception as e:
        logger.exception("Unexpected error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Get Card ----------------
@app.get("/card/{username}")
async def get_card(username: str):

    file_path = os.path.join(CARDS_DIR, f"{username}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)

    file_path = os.path.join(CARDS_DIR, f"{username.lower()}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)

    raise HTTPException(status_code=404, detail="Card not found")


# ---------------- Health Check ----------------
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ---------------- Local Run ----------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)