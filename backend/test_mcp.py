import asyncio
import json
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

async def test_end_to_end():
    username = "torvalds"
    print(f"--- Testing end-to-end for: {username} ---")

    # 1. Scrape GitHub
    print("\n1. Calling scrape_github...")
    github_data = await scrape_github(username)
    if "error" in github_data:
        print(f"FAILED: scrape_github - {github_data['error']}")
        return

    # 2. Analyze Profile
    print("2. Calling analyze_profile...")
    analysis = await analyze_profile(github_data)
    if "error" in analysis:
        print(f"FAILED: analyze_profile - {analysis['error']}")
        return
    
    # 3. Generate HTML Card
    print("3. Calling generate_card_html...")
    html = await generate_card_html(username, github_data, analysis)
    
    # 4. Print Results
    print("\n--- Analysis Results ---")
    print(f"Card Theme: {analysis.get('card_theme')}")
    print(f"Developer Vibe: {analysis.get('developer_vibe')}")
    
    # 5. Save (Optional but good to test)
    path = await save_card(username, html)
    print(f"\nCard saved to: {path}")
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
