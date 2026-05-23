import os
import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.errors.already_exists_error import AlreadyExistsError
from agent import github_card_agent
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="GitHub Dev Card Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ADK Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Initialize ADK Runner
runner = Runner(
    app_name="github-card-generator",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
    auto_create_session=True # Let the runner handle session creation
)

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    username: str

async def check_github_user(username: str) -> bool:
    """Check if a GitHub user exists."""
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    async with httpx.AsyncClient(headers=headers) as client:
        try:
            res = await client.get(f"https://api.github.com/users/{username}")
            return res.status_code == 200
        except Exception as e:
            logger.error(f"Error checking GitHub user {username}: {e}")
            return False

@app.post("/generate")
async def generate(request: GenerateRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
        
    user_key = username.lower()
    session_id = f"session_{user_key}"
    
    logger.info(f"--- Request received for user: {username} ---")

    # 1. Validation
    if not await check_github_user(username):
        logger.warning(f"GitHub user not found: {username}")
        raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found.")

    try:
        # 2. Agent Execution
        content = types.Content(
            role="user",
            parts=[
                types.Part(text=f"Generate a dev card for {username}")
            ]
        )

        logger.info(f"Starting agent for {username}...")
        
        # runner.run_async returns an AsyncGenerator of Events
        # With auto_create_session=True, we don't need manual create_session calls
        events = runner.run_async(
            user_id=user_key,
            session_id=session_id,
            new_message=content
        )
        
        async for event in events:
            # We must consume the generator for the agent to run tools
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[{username}] Agent Event: {event}")
        
        logger.info(f"Agent finished run for {username}")

        # 4. Result Verification
        card_filename = f"{username}.html"
        card_path = os.path.join(CARDS_DIR, card_filename)
        
        if not os.path.exists(card_path):
            card_path = os.path.join(CARDS_DIR, f"{user_key}.html")
            card_filename = f"{user_key}.html"
            
        if not os.path.exists(card_path):
            logger.error(f"Card file not found for {username}")
            raise HTTPException(
                status_code=500,
                detail="Agent finished but failed to generate the card file."
            )

        with open(card_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        logger.info(f"Successfully generated card for {username}")
        return {
            "status": "success",
            "username": username,
            "card_url": f"/static/cards/{card_filename}",
            "html": html_content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error for {username}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}")
async def get_card(username: str):
    """Serve a saved card with case-insensitive fallback."""
    # Try exact match first
    file_path = os.path.join(CARDS_DIR, f"{username}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    # Try lowercase fallback
    file_path = os.path.join(CARDS_DIR, f"{username.lower()}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
        
    raise HTTPException(status_code=404, detail=f"Card for '{username}' not found.")

@app.get("/health")
async def health():
    """Cloud Run health check."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
