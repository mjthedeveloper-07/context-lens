import sys
import os
from .indexer import ContextIndexer
from .watcher import ContextWatcher
from .mcp_server import mcp, subscriptions

def main():
    print("Initializing ContextLens (v2027 Vision)...")

    # Initialize indexer with config
    indexer = ContextIndexer(config_path="contextlens_config.yaml")

    # Start background watcher with subscription sharing
    watcher = ContextWatcher(indexer, interval=30, subscriptions=subscriptions)
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
