import os
from google.adk.agents import Agent
from google.adk.tools import McpToolset
from mcp.client.stdio import StdioServerParameters

# Configure MCP Server connection (stdio transport)
mcp_server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "mcp_server.py"))

server_params = StdioServerParameters(
    command="python",
    args=[mcp_server_path]
)

# System Instruction
SYSTEM_INSTRUCTION = (
    "You are a GitHub profile analyst and dev card generator. "
    "When a user gives you a GitHub username, you ALWAYS follow this exact sequence: "
    "first call scrape_github, then analyze_profile with the result, "
    "then generate_card_html with all three inputs, then save_card. "
    "Never skip steps. Be enthusiastic about developers' work. "
    "If the profile is private or doesn't exist, say so clearly."
)

# Create the MCP Toolset
# McpToolset requires keyword-only arguments for connection_params
mcp_toolset = McpToolset(connection_params=server_params)

# Define the Agent
github_card_agent = Agent(
    name="github_card_agent",
    instruction=SYSTEM_INSTRUCTION, # ADK uses 'instruction' (singular) for Agent
    model="gemini-2.5-flash",
    tools=[mcp_toolset]
)
