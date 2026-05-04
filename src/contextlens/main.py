import sys
import os
from .indexer import ContextIndexer
from .watcher import ContextWatcher
from .mcp_server import mcp

def main():
    print("Initializing ContextIndex...")
    
    # Initialize indexer
    indexer = ContextIndexer()
    
    # Start background watcher
    watcher = ContextWatcher(indexer, interval=30)
    watcher.start()
    
    try:
        # Start MCP Server
        # FastMCP uses click, so we call .run()
        # This will block until the server is stopped
        mcp.run()
    except KeyboardInterrupt:
        print("\nStopping ContextIndex...")
    finally:
        watcher.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
