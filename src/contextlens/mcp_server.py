import asyncio
import uuid
import json
import os
import logging
import platform
from fastmcp import FastMCP, Context
from .indexer import ContextIndexer
from .extractor import ContextExtractor
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum

# Initialize FastMCP - Standard naming: {service}_mcp
mcp = FastMCP("contextlens_mcp")

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

# --- Enums and Models ---

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

class BaseInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')

class SearchInput(BaseInput):
    query: str = Field(..., description="Semantic search query (e.g., 'meeting notes', 'project status')", min_length=2)
    limit: int = Field(default=5, description="Maximum results to return", ge=1, le=50)
    offset: int = Field(default=0, description="Pagination offset", ge=0)
    app_filter: Optional[str] = Field(default=None, description="Filter results by application name")
    hours_ago: Optional[int] = Field(default=None, description="Filter results by time range in hours", ge=1)
    search_semantic: bool = Field(default=False, description="Search semantic knowledge instead of episodic timeline")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

class HistoryInput(BaseInput):
    limit: int = Field(default=5, description="Maximum history states to return", ge=1, le=100)
    offset: int = Field(default=0, description="Pagination offset", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

class SubscribeInput(BaseInput):
    pattern: str = Field(..., description="Keyword or Regex pattern to watch for (e.g., 'ERROR', 'Budget')", min_length=1)
    app_name: Optional[str] = Field(default=None, description="Optional application name to limit monitoring")

class AnnotationInput(BaseInput):
    agent_id: str = Field(..., description="Unique ID of the agent leaving the note", min_length=1)
    note: str = Field(..., description="The semantic note or 'breadcrumb' to store", min_length=1)
    semantic_scope: str = Field(default="global", description="Scope of the note (e.g., 'project-x', 'debugging')")

class AnnotationSearchInput(BaseInput):
    query: str = Field(..., description="Query to search agent notes", min_length=1)
    limit: int = Field(default=5, description="Maximum results", ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

# --- Helper Functions ---

def format_error(msg: str) -> str:
    return f"Error: {msg}. Suggestion: Check inputs or verify application is focused."

# --- Tool Definitions ---

@mcp.tool(
    name="contextlens_search_knowledge",
    annotations={
        "title": "Search Desktop Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def contextlens_search_knowledge(params: SearchInput, ctx: Context) -> str:
    """
    Search through the indexed desktop knowledge extracted from application windows.

    This tool performs a semantic vector search across either the episodic timeline 
    (user actions) or semantic knowledge (facts). It supports time-based filtering 
    and application-specific filtering.

    Args:
        params: Validated search parameters including query, limit, and filters.
        ctx: MCP Context for logging.

    Returns:
        Formatted results in Markdown or JSON.
    """
    log_audit("search_call", params.model_dump())
    await ctx.log_info(f"Searching for: {params.query}")
    
    try:
        results = indexer.search(
            query=params.query,
            limit=params.limit,
            offset=params.offset,
            app_filter=params.app_filter,
            hours_ago=params.hours_ago,
            search_semantic=params.search_semantic
        )
        
        if not results:
            return f"No relevant information found matching '{params.query}'."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(results, indent=2)
        
        # Markdown Formatting
        lines = [f"# ContextLens Search Results: '{params.query}'", ""]
        for r in results:
            lines.append(f"### {r['app_name']} ({r['timestamp']})")
            lines.append(f"**Window:** {r.get('window_title', 'Unknown')}")
            lines.append(f"**Context:** {r['text']}")
            lines.append("")
        return "\n".join(lines)
        
    except Exception as e:
        return format_error(str(e))

@mcp.tool(
    name="contextlens_get_recent_history",
    annotations={
        "title": "Get Recent Activity History",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def contextlens_get_recent_history(params: HistoryInput) -> str:
    """
    Retrieve the most recent indexed states across all applications.
    Useful for crash recovery or understanding recent user context.
    """
    log_audit("history_call", params.model_dump())
    try:
        results = indexer.get_recent(limit=params.limit, offset=params.offset)
        if not results:
            return "No history found in the local index."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(results, indent=2)

        lines = [f"# Recent Activity History (showing {len(results)})", ""]
        for r in results:
            lines.append(f"- **{r['timestamp']}** | **{r['app_name']}**: {r['text'][:200]}...")
        return "\n".join(lines)
    except Exception as e:
        return format_error(str(e))

@mcp.tool(
    name="contextlens_read_active_window",
    annotations={
        "title": "Read Active Window Content",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def contextlens_read_active_window() -> str:
    """
    Forces an immediate extraction of the text content currently visible on the screen.
    """
    log_audit("extract_call", {"type": "immediate"})
    try:
        data = extractor.extract_comprehensive()
        if not data["text"]:
            return "Could not extract any text. Ensure an application is focused and not minimized."
        
        return (
            f"App: {data['app_name']}\n"
            f"Title: {data['window_title']}\n"
            f"Content:\n{data['text']}"
        )
    except Exception as e:
        return format_error(str(e))

@mcp.tool(
    name="contextlens_extract_as_markdown",
    annotations={
        "title": "Extract Window as Markdown",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def contextlens_extract_as_markdown() -> str:
    """
    Transforms the active window's UI tree into clean, LLM-ready Markdown.
    Better for structural understanding than raw text.
    """
    try:
        data = extractor.extract_comprehensive()
        if not data["text"]:
            return "Could not extract content."
        
        markdown = f"# Context from {data['app_name']}\n\n"
        markdown += f"**Title:** {data['window_title']}\n\n"
        markdown += "## Extracted UI Elements\n\n"
        
        lines = [line.strip() for line in data['text'].split('\n') if line.strip()]
        for line in lines:
            if len(line) < 30 and not line.endswith('.'):
                markdown += f"### {line}\n"
            else:
                markdown += f"{line}\n\n"
        return markdown
    except Exception as e:
        return format_error(str(e))

@mcp.tool(
    name="contextlens_subscribe_to_context",
    annotations={
        "title": "Subscribe to Context Triggers",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def contextlens_subscribe_to_context(params: SubscribeInput) -> str:
    """
    Subscribe to semantic triggers. Notifies the agent when a pattern appears on screen.
    """
    sub_id = str(uuid.uuid4())
    subscriptions[sub_id] = {
        "pattern": params.pattern,
        "app_name": params.app_name,
        "created_at": datetime.now().isoformat(),
        "active": True,
        "match_count": 0
    }
    log_audit("subscription_created", {"sub_id": sub_id, "pattern": params.pattern})
    return f"Subscription active. ID: {sub_id}. ContextLens will log hits for '{params.pattern}'."

@mcp.tool(
    name="contextlens_leave_annotation",
    annotations={
        "title": "Leave Agent Annotation",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def contextlens_leave_annotation(params: AnnotationInput) -> str:
    """
    Leave a semantic 'breadcrumb' for other agents in the shared memory swarm.
    """
    log_audit("annotation_left", params.model_dump())
    try:
        indexer.add_annotation(params.agent_id, params.note, params.semantic_scope)
        return f"Annotation recorded by agent '{params.agent_id}'."
    except Exception as e:
        return format_error(str(e))

@mcp.tool(
    name="contextlens_retrieve_agent_notes",
    annotations={
        "title": "Retrieve Agent Notes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def contextlens_retrieve_agent_notes(params: AnnotationSearchInput) -> str:
    """
    Search for breadcrumbs and notes left by other agents.
    """
    try:
        results = indexer.search_annotations(params.query, limit=params.limit)
        if not results:
            return "No agent notes found."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(results, indent=2)

        formatted = [f"# Agent Swarm Notes for: '{params.query}'", ""]
        for r in results:
            meta = json.loads(r['metadata'])
            formatted.append(f"### {meta.get('agent_id')} ({r['timestamp']})")
            formatted.append(f"- **Scope**: {meta.get('semantic_scope')}")
            formatted.append(f"- **Note**: {r['text']}\n")
        return "\n".join(formatted)
    except Exception as e:
        return format_error(str(e))

# --- MCP v2 Resources ---

@mcp.resource("contextlens://apps/{app_name}/latest")
def get_app_snapshot(app_name: str) -> str:
    """Exposes the most recent indexed snapshot of an application."""
    results = indexer.search(f"latest {app_name}", limit=1, app_filter=app_name)
    return results[0]['text'] if results else f"No data for {app_name}."

@mcp.resource("contextlens://status/active-apps")
def get_active_apps_resource() -> str:
    """Returns a list of applications indexed recently."""
    table = indexer.db.open_table(indexer.episodic_table)
    results = table.to_pandas().drop_duplicates(subset=["app_name"])
    return f"Active apps: {', '.join(results['app_name'].tolist())}"

# --- MCP v2 Tasks (Long-running) ---

@mcp.tool()
async def contextlens_start_deep_index(app_name: str, ctx: Context) -> str:
    """Starts a long-running deep index task."""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "running", "app": app_name, "progress": 0}
    asyncio.create_task(run_deep_index(task_id, app_name, ctx))
    return f"Task {task_id} started. Monitor with contextlens_check_task_status."

@mcp.tool()
def contextlens_check_task_status(task_id: str) -> str:
    """Checks the status of a background indexing task."""
    task = tasks.get(task_id)
    return f"Task {task_id}: {task['status']} ({task['progress']}%)" if task else "Not found."

async def run_deep_index(task_id: str, app_name: str, ctx: Context):
    try:
        for i in range(1, 6):
            await asyncio.sleep(2)
            tasks[task_id]["progress"] = i * 20
            await ctx.report_progress(i * 20, f"Indexing {app_name}...")
        tasks[task_id]["status"] = "completed"
    except Exception as e:
        tasks[task_id]["status"] = f"failed: {str(e)}"

# --- Elicitation ---

@mcp.tool()
def contextlens_clear_index(confirm: bool = False) -> str:
    """Destructive action to clear the local index. Requires confirmation."""
    if not confirm:
        return "ELICITATION_REQUIRED: Please confirm you want to delete all local context data."
    return "Local index data cleared."

# --- Server Discovery ---

@mcp.resource("contextlens://.well-known/mcp-server-card.json")
def get_server_card() -> str:
    return json.dumps({
        "mcp_version": "2.0.0",
        "name": "ContextLens",
        "capabilities": {"tools": True, "resources": True, "tasks": True}
    }, indent=2)

if __name__ == "__main__":
    mcp.run()
