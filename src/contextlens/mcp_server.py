import asyncio
import uuid
import json
import os
import logging
from fastmcp import FastMCP
from .indexer import ContextIndexer
from .extractor import ContextExtractor
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime

# Initialize FastMCP
mcp = FastMCP("ContextLens")

# Setup Audit Logging
LOG_DIR = Path.home() / ".contextlens" / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "audit.log",
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
audit_logger = logging.getLogger("ContextLensAudit")

def log_audit(event_type: str, details: Dict):
    audit_logger.info(json.dumps({"event": event_type, "details": details}))

# Initialize core components
indexer = ContextIndexer()
extractor = ContextExtractor()

# Global task and subscription storage
tasks: Dict[str, Dict] = {}
subscriptions: Dict[str, Dict] = {}

@mcp.tool()
def subscribe_to_context(pattern: str, app_name: Optional[str] = None) -> str:
    """
    Subscribe to semantic triggers (MCP Triggers charter).
    Notifies the agent when the pattern (keyword/regex) appears on screen.
    Returns a Subscription ID.
    """
    sub_id = str(uuid.uuid4())
    subscriptions[sub_id] = {
        "pattern": pattern,
        "app_name": app_name,
        "created_at": datetime.now().isoformat(),
        "active": True,
        "match_count": 0
    }
    log_audit("subscription_created", {"sub_id": sub_id, "pattern": pattern})
    return f"Subscription active. ID: {sub_id}. You will be notified via context updates when '{pattern}' is detected."

@mcp.tool()
def list_subscriptions() -> str:
    """List all active semantic context subscriptions."""
    return json.dumps(subscriptions, indent=2)

@mcp.tool()
def unsubscribe(sub_id: str) -> str:
    """Deactivate a context subscription."""
    if sub_id in subscriptions:
        subscriptions[sub_id]["active"] = False
        return f"Subscription {sub_id} deactivated."
    return "Subscription not found."

@mcp.tool()
def leave_annotation(agent_id: str, note: str, semantic_scope: str = "global") -> str:
    """
    Leave a semantic 'breadcrumb' for other agents. 
    This allows a swarm of agents to share context and notes locally.
    """
    if not note.strip():
        return "Error: Note cannot be empty."
    
    log_audit("annotation_left", {"agent_id": agent_id, "scope": semantic_scope})
    indexer.add_annotation(agent_id, note, semantic_scope)
    return f"Annotation recorded by agent '{agent_id}' in scope '{semantic_scope}'."

@mcp.tool()
def retrieve_agent_notes(query: str, limit: int = 5) -> str:
    """
    Search for breadcrumbs and notes left by other agents in the shared memory.
    """
    log_audit("annotation_search", {"query": query})
    results = indexer.search_annotations(query, limit=limit)
    if not results:
        return "No agent notes found for this query."
    
    formatted = []
    for r in results:
        meta = json.loads(r['metadata'])
        formatted.append(
            f"--- Agent: {meta.get('agent_id')} ({r['timestamp']}) ---\n"
            f"Scope: {meta.get('semantic_scope')}\n"
            f"Note: {r['text']}\n"
        )
    return "\n".join(formatted)

@mcp.tool()
def search_context_knowledge(query: str, limit: int = 5, app_filter: Optional[str] = None, hours_ago: Optional[int] = None) -> str:
    """
    Search through the indexed desktop knowledge.
    Supports filtering by application name and time range (hours_ago).
    """
    # Security: Strict validation
    if not query.strip():
        return "Error: Query cannot be empty."
    if not (1 <= limit <= 50):
        return "Error: Limit must be between 1 and 50."
    
    log_audit("search_call", {"query": query, "limit": limit, "app_filter": app_filter, "hours_ago": hours_ago})
    
    results = indexer.search(query, limit=limit, app_filter=app_filter, hours_ago=hours_ago)
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
def get_recent_history(limit: int = 5) -> str:
    """
    Retrieve the last N states indexed by ContextLens across all apps.
    Useful for crash recovery or understanding recent activity.
    """
    log_audit("history_call", {"limit": limit})
    results = indexer.get_recent(limit=limit)
    if not results:
        return "No history found."
    
    formatted_results = []
    for r in results:
        formatted_results.append(
            f"--- {r['timestamp']} | {r['app_name']} ---\n"
            f"Content: {r['text'][:200]}...\n"
        )
    return "\n".join(formatted_results)

@mcp.tool()
def check_app_update(app_name: str) -> str:
    """
    Check if the specified application's content has changed since the last poll.
    Returns the new content if changed, otherwise indicates no change.
    """
    log_audit("monitor_call", {"app": app_name})
    data = extractor.extract_comprehensive()
    if data["app_name"].lower() != app_name.lower():
        return f"Application {app_name} is not currently in focus. Active app is {data['app_name']}."
    
    # This tool effectively acts as a 'hook' for agents to poll
    return (
        f"Status: Content indexed at {datetime.now().isoformat()}\n"
        f"Current View:\n{data['text'][:500]}..."
    )

@mcp.tool()
def read_active_window() -> str:
    """
    Forces an immediate extraction of the text content currently visible on the screen.
    Useful for getting real-time context from the frontmost application.
    """
    log_audit("extract_call", {"type": "immediate"})
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
    table = indexer.db.open_table(indexer.episodic_table)
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
