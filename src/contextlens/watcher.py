import time
import hashlib
import threading
from .extractor import ContextExtractor
from .indexer import ContextIndexer

class ContextWatcher:
    def __init__(self, indexer: ContextIndexer, interval: int = 30):
        self.indexer = indexer
        self.extractor = ContextExtractor()
        self.interval = interval
        self.last_hash = ""
        self.running = False
        self._thread = None

    def _get_hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _loop(self):
        while self.running:
            try:
                # 1. Standard Comprehensive Extraction (Accessibility/OCR)
                data = self.extractor.extract_comprehensive()
                current_hash = self._get_hash(data["text"])
                
                # Check for significant changes
                is_new_content = current_hash != self.last_hash and data["text"]
                
                if is_new_content:
                    # Index full text for episodic memory
                    self.indexer.add_content(
                        text=data["text"],
                        app_name=data["app_name"],
                        window_title=data["window_title"],
                        is_semantic=False
                    )
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
