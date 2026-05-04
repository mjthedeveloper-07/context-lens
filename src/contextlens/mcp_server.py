import asyncio
import uuid
import json
from fastmcp import FastMCP
from .indexer import ContextIndexer
from .extractor import ContextExtractor
from typing import Optional, Dict

# Initialize FastMCP
mcp = FastMCP("ContextLens")

# Initialize core components
indexer = ContextIndexer()
extractor = ContextExtractor()

# Global task storage for SEP-1686 (Async Tasks)
tasks: Dict[str, Dict] = {}

@mcp.tool()
def search_context_knowledge(query: str, limit: int = 5, app_filter: Optional[str] = None) -> str:
    """
    Search through the indexed desktop knowledge (extracted from app windows).
    Returns the most relevant text snippets found locally.
    """
    # Security: Strict validation of limit
    if not (1 <= limit <= 50):
        return "Error: Limit must be between 1 and 50."
    
    results = indexer.search(query, limit=limit, app_filter=app_filter)
    if not results:
        return "No relevant information found in the local index."
    
    formatted_results = []
    for r in results:
        formatted_results.append(
            f"--- App: {r['app_name']} ({r['timestamp']}) ---\n"
            f"Context: {r['text']}\n"
        )
    return "\n".join(formatted_results)

@mcp.tool()
def read_active_window() -> str:
    """
    Forces an immediate extraction of the text content currently visible on the screen.
    Useful for getting real-time context from the frontmost application.
    """
    data = extractor.extract_comprehensive()
    if not data["text"]:
        return "Could not extract any text from the active window."
    
    return (
        f"App: {data['app_name']}\n"
        f"Title: {data['window_title']}\n"
        f"Content:\n{data['text']}"
    )

@mcp.tool()
def extract_as_markdown() -> str:
    """
    New Integration: Firecrawl-style Markdown extraction.
    Transforms the active window's UI tree into clean, LLM-ready Markdown.
    """
    data = extractor.extract_comprehensive()
    if not data["text"]:
        return "Could not extract any text."
    
    # Simple heuristic to 'markdown-ify' the text
    # In a real implementation, this would parse the accessibility tree more deeply
    markdown = f"# Context from {data['app_name']}\n\n"
    markdown += f"**Title:** {data['window_title']}\n\n"
    markdown += "## Extracted Content\n\n"
    
    # Split text into lines and clean up
    lines = [line.strip() for line in data['text'].split('\n') if line.strip()]
    for line in lines:
        if len(line) < 30 and not line.endswith('.'):
            markdown += f"### {line}\n"
        else:
            markdown += f"{line}\n\n"
            
    return markdown

# --- MCP v2 Resources ---

@mcp.resource("contextlens://apps/{app_name}/latest")
def get_app_snapshot(app_name: str) -> str:
    """
    Exposes the most recent indexed snapshot of a specific application as a read-only resource.
    """
    results = indexer.search(f"latest content from {app_name}", limit=1, app_filter=app_name)
    if not results:
        return f"No indexed data found for {app_name}."
    
    return f"Latest Snapshot for {app_name} ({results[0]['timestamp']}):\n\n{results[0]['text']}"

@mcp.resource("contextlens://status/active-apps")
def get_active_apps_resource() -> str:
    """
    Returns a list of applications that have been indexed recently.
    """
    table = indexer.db.open_table(indexer.table_name)
    results = table.to_pandas().drop_duplicates(subset=["app_name"])
    apps = results["app_name"].tolist()
    return f"Recently indexed apps: {', '.join(apps)}"

# --- MCP v2 Tasks (SEP-1686 Implementation) ---

@mcp.tool()
async def start_deep_index(app_name: str) -> str:
    """
    Starts a long-running 'deep index' of an application (SEP-1686 Task pattern). 
    Returns a Task ID.
    """
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "running", "app": app_name, "progress": 0}
    
    # Start the background task
    asyncio.create_task(run_deep_index(task_id, app_name))
    
    return f"Deep index task started for {app_name}. Task ID: {task_id}. Use check_task_status to monitor."

@mcp.tool()
def check_task_status(task_id: str) -> str:
    """
    Checks the status of a background indexing task.
    """
    task = tasks.get(task_id)
    if not task:
        return "Task not found."
    
    return f"Task {task_id} for {task['app']} is {task['status']} ({task['progress']}%)."

async def run_deep_index(task_id: str, app_name: str):
    """
    Simulated long-running extraction task.
    """
    try:
        for i in range(1, 6):
            await asyncio.sleep(2) # Faster for testing
            tasks[task_id]["progress"] = i * 20
        
        tasks[task_id]["status"] = "completed"
    except Exception as e:
        tasks[task_id]["status"] = f"failed: {str(e)}"

# --- Elicitation (SEP-382 Implementation Pattern) ---

@mcp.tool()
def clear_index_data(confirm: bool = False) -> str:
    """
    Destructive action demonstrating Elicitation.
    If 'confirm' is false, it prompts the agent to ask the user for confirmation.
    """
    if not confirm:
        return "ELICITATION_REQUIRED: This action will delete all local desktop context. Please ask the user to confirm by setting 'confirm=True' if they wish to proceed."
    
    # Perform deletion logic (mocked here)
    return "SUCCESS: Local index data cleared."

# --- Discovery (Server Card) ---

@mcp.resource("contextlens://.well-known/mcp-server-card.json")
def get_server_card() -> str:
    """
    Returns the MCP Server Card for automatic discovery.
    """
    card = {
        "mcp_version": "2.0.0",
        "name": "ContextLens",
        "description": "The Zero-API Knowledge Bridge for desktop context.",
        "capabilities": {
            "tools": True,
            "resources": True,
            "tasks": True
        }
    }
    return json.dumps(card, indent=2)
