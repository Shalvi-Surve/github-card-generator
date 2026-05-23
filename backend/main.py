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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="GitHub Dev Card Generator API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files setup
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Request model
class GenerateRequest(BaseModel):
    username: str


# Check GitHub user exists
async def check_github_user(username: str) -> bool:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    async with httpx.AsyncClient(headers=headers) as client:
        try:
            res = await client.get(f"https://api.github.com/users/{username}")
            return res.status_code == 200
        except Exception as e:
            logger.error(f"GitHub check failed: {e}")
            return False


# MAIN ENDPOINT
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
        # Fake/simple generation (safe for Render right now)
        logger.info(f"Generating card for {username}")

        card_filename = f"{user_key}.html"
        card_path = os.path.join(CARDS_DIR, card_filename)

        # Create HTML file
        html_content = f"""
        <html>
        <head>
            <title>{username} GitHub Card</title>
            <style>
                body {{
                    font-family: Arial;
                    background: #0d1117;
                    color: white;
                    text-align: center;
                    padding-top: 50px;
                }}
                .card {{
                    background: #161b22;
                    padding: 20px;
                    border-radius: 12px;
                    display: inline-block;
                }}
                h1 {{
                    color: #58a6ff;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>{username}</h1>
                <p>GitHub Dev Card Generated 🚀</p>
            </div>
        </body>
        </html>
        """

        with open(card_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        if not os.path.exists(card_path):
            raise HTTPException(
                status_code=500,
                detail="Failed to create card file"
            )

        return {
            "status": "success",
            "username": username,
            "card_url": f"/static/cards/{card_filename}",
            "html": html_content
        }

    except Exception as e:
        logger.exception("Error generating card")
        raise HTTPException(status_code=500, detail=str(e))


# Serve card
@app.get("/card/{username}")
async def get_card(username: str):
    file_path = os.path.join(CARDS_DIR, f"{username}.html")

    if os.path.exists(file_path):
        return FileResponse(file_path)

    file_path = os.path.join(CARDS_DIR, f"{username.lower()}.html")

    if os.path.exists(file_path):
        return FileResponse(file_path)

    raise HTTPException(status_code=404, detail="Card not found")


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}


# Local run
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)