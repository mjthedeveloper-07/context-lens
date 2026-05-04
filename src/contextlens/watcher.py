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
                data = self.extractor.extract_comprehensive()
                current_hash = self._get_hash(data["text"])
                
                if current_hash != self.last_hash and data["text"]:
                    self.indexer.add_content(
                        text=data["text"],
                        app_name=data["app_name"],
                        window_title=data["window_title"]
                    )
                    self.last_hash = current_hash
                    print(f"Indexed content from {data['app_name']}")
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
