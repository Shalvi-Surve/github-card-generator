import os
import httpx
import json
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Any
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Initialize FastMCP server
mcp = FastMCP("GitHub Dev Card Generator")

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

@mcp.tool()
async def scrape_github(username: str) -> Dict[str, Any]:
    """Fetch GitHub statistics and top repos for a given user."""
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async with httpx.AsyncClient(headers=headers) as client:
        # Fetch user profile
        user_res = await client.get(f"{GITHUB_API_URL}/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"User not found or API error: {user_res.status_code}"}
        user_data = user_res.json()

        # Fetch repos
        repos_res = await client.get(f"{GITHUB_API_URL}/users/{username}/repos?sort=stars&per_page=30")
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

    # Sort by stars and get top 6
    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    
    # Aggregate languages
    languages = [repo.get("language") for repo in repos_data if repo.get("language")]
    lang_counts = Counter(languages).most_common(5)
    
    return {
        "name": user_data.get("name") or username,
        "avatar_url": user_data.get("avatar_url"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "top_repos": [
            {
                "name": r.get("name"),
                "stars": r.get("stargazers_count"),
                "language": r.get("language"),
                "description": r.get("description")
            } for r in top_repos
        ],
        "most_used_languages": [lang for lang, count in lang_counts]
    }

@mcp.tool()
async def analyze_profile(github_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze GitHub data using Gemini 2.5 Flash to determine developer vibe and theme."""
    if not GOOGLE_API_KEY:
        return {"error": "GOOGLE_API_KEY not set"}

    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    Analyze this GitHub profile and return a JSON object. 
    Be creative and clever.
    
    Data: {json.dumps(github_data)}
    
    JSON format:
    {{
        "developer_vibe": "1 sentence personality",
        "top_skills": ["skill1", "skill2", "skill3"],
        "fun_fact": "something clever inferred from their repos",
        "card_theme": "hacker" | "builder" | "researcher" | "designer" | "open-source-hero"
    }}
    
    Return ONLY the raw JSON object.
    """
    
    response = model.generate_content(prompt)
    try:
        # Strip potential markdown formatting
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        return json.loads(text)
    except Exception as e:
        return {
            "developer_vibe": f"An enigmatic developer with {github_data.get('public_repos')} repos.",
            "top_skills": github_data.get('most_used_languages', [])[:3],
            "fun_fact": "Their code is so good, it's almost suspicious.",
            "card_theme": "builder",
            "parsing_error": str(e)
        }

@mcp.tool()
async def generate_card_html(username: str, github_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Generate a self-contained HTML string for a beautiful dev card."""
    theme = analysis.get("card_theme", "builder")
    themes = {
        "hacker": {"bg": "#0a0a0a", "text": "#00ff41", "accent": "#008f11"},
        "builder": {"bg": "#ffffff", "text": "#1a1a1a", "accent": "#007bff"},
        "researcher": {"bg": "#f8f9fa", "text": "#2c3e50", "accent": "#e74c3c"},
        "designer": {"bg": "#fff5f5", "text": "#4a4a4a", "accent": "#ff6b6b"},
        "open-source-hero": {"bg": "#f0fff4", "text": "#22543d", "accent": "#48bb78"}
    }
    t = themes.get(theme, themes["builder"])
    
    repos_html = "".join([
        f"<div style='margin-bottom: 10px; border-left: 3px solid {t['accent']}; padding-left: 10px;'>"
        f"<strong>{r['name']}</strong> ({r['stars']} ⭐) - {r['language']}<br>"
        f"<small>{r['description'] or ''}</small></div>"
        for r in github_data.get("top_repos", [])[:3]
    ])
    
    skills_html = "".join([
        f"<span style='background: {t['accent']}; color: white; padding: 2px 8px; border-radius: 12px; margin-right: 5px; font-size: 0.8rem;'>{s}</span>"
        for s in analysis.get("top_skills", [])
    ])

    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: {t['bg']}; color: {t['text']}; padding: 25px; border-radius: 15px; width: 400px; border: 1px solid #ddd; box-shadow: 0 10px 20px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="{github_data.get('avatar_url')}" style="width: 80px; height: 80px; border-radius: 50%; margin-right: 20px; border: 3px solid {t['accent']};">
            <div>
                <h2 style="margin: 0;">{github_data.get('name')}</h2>
                <p style="margin: 5px 0; font-size: 0.9rem; opacity: 0.8;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; margin-bottom: 15px;">"{analysis.get('developer_vibe')}"</p>
        <div style="margin-bottom: 15px;">{skills_html}</div>
        <div style="display: flex; justify-content: space-around; margin-bottom: 20px; font-weight: bold; border-top: 1px solid #eee; border-bottom: 1px solid #eee; padding: 10px 0;">
            <div>Repos: {github_data.get('public_repos')}</div>
            <div>Followers: {github_data.get('followers')}</div>
        </div>
        <h4 style="margin-top: 0; color: {t['accent']};">Top Projects</h4>
        {repos_html}
        <div style="margin-top: 15px; font-size: 0.8rem; background: #eee; padding: 5px; border-radius: 5px;">
            <strong>Fun Fact:</strong> {analysis.get('fun_fact')}
        </div>
    </div>
    """
    return html

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the HTML to static/cards/{username}.html and return the path."""
    os.makedirs("static/cards", exist_ok=True)
    file_path = f"static/cards/{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
