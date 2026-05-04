import time
import hashlib
import threading
from .extractor import ContextExtractor
from .indexer import ContextIndexer

import re

class ContextWatcher:
    def __init__(self, indexer: ContextIndexer, interval: int = 30, subscriptions: Dict = None):
        self.indexer = indexer
        self.extractor = ContextExtractor()
        self.interval = interval
        self.subscriptions = subscriptions if subscriptions is not None else {}
        self.last_hash = ""
        self.running = False
        self._thread = None

    def _get_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _check_triggers(self, text: str, app_name: str):
        """Check if any subscription patterns match the current screen text."""
        for sub_id, sub in self.subscriptions.items():
            if not sub["active"]:
                continue

            # App filter check
            if sub["app_name"] and sub["app_name"].lower() != app_name.lower():
                continue

            # Pattern match (simple regex/keyword)
            if re.search(sub["pattern"], text, re.IGNORECASE):
                sub["match_count"] += 1
                # Log the trigger event - in a full MCP implementation, this would emit an SSE event
                print(f"🚨 TRIGGER MATCH: Subscription '{sub['pattern']}' found in {app_name}!")
                self.indexer.add_event(
                    app_name=app_name,
                    summary=f"Trigger Alert: Matched pattern '{sub['pattern']}'",
                    action_type="trigger_hit"
                )

    def _loop(self):
        while self.running:
            try:
                # 1. Standard Comprehensive Extraction
                data = self.extractor.extract_comprehensive()
                current_text = data["text"]
                current_hash = self._get_hash(current_text)

                # Check for significant changes
                if current_hash != self.last_hash and current_text:
                    self.indexer.add_content(
                        text=current_text,
                        app_name=data["app_name"],
                        window_title=data["window_title"],
                        is_semantic=False
                    )

                    # Check semantic triggers (Phase 2 Roadmap)
                    self._check_triggers(current_text, data["app_name"])

                    self.last_hash = current_hash
                    print(f"Indexed content from {data['app_name']}")


                # 2. Vision Model Integration (Phase 3)
                # We do this periodically regardless of text hash to capture visual state
                screenshot = self.extractor.get_screenshot()
                if screenshot:
                    vision_summary = self.extractor.vision.analyze_screen(screenshot)
                    if vision_summary:
                        # Record a visual 'event' in episodic memory
                        self.indexer.add_event(
                            app_name=data["app_name"],
                            summary=f"Visual: {vision_summary}",
                            action_type="visual_observe"
                        )
                        print(f"Vision Event: {vision_summary}")

                # 3. Detect App Switches for Episodic Timeline
                # (Heuristic: If app_name changed, record a 'switch' event)
                # In a more advanced version, we'd compare process IDs
                
            except Exception as e:
                print(f"Watcher Error: {e}")
            
            time.sleep(self.interval)

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print("ContextIndex Watcher started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()
        print("ContextIndex Watcher stopped.")
