import platform
import subprocess
import mss
from PIL import Image
import pytesseract
from typing import Optional, Dict

# Conditional import for macOS
if platform.system() == "Darwin":
    from AppKit import NSWorkspace
    import Quartz

class ContextExtractor:
    def __init__(self):
        self.system = platform.system()

    def get_active_window_info(self) -> Optional[Dict]:
        if self.system == "Darwin":
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            if not active_app:
                return None
            
            return {
                "app_name": active_app.localizedName(),
                "pid": active_app.processIdentifier()
            }
        # TODO: Implement for Windows/Linux
        return None

    def extract_text_accessibility(self) -> str:
        if self.system == "Darwin":
            # Use AppleScript as a high-level bridge to accessibility
            # This is often more reliable than low-level C-bindings for quick prototyping
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    set allElements to every UI element
                    set resultText to ""
                    repeat with el in allElements
                        try
                            set resultText to resultText & (value of el as string) & " "
                        end try
                    end repeat
                    return resultText
                end tell
            end tell
            '''
            try:
                proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
                return proc.stdout.strip()
            except Exception:
                return ""
        return ""

    def extract_text_ocr(self) -> str:
        try:
            with mss.mss() as sct:
                # Capture the primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Run OCR
                text = pytesseract.image_to_string(img)
                return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def extract_comprehensive(self) -> Dict:
        info = self.get_active_window_info()
        if not info:
            return {"text": "", "app_name": "unknown", "window_title": "unknown"}

        # Try Accessibility first
        text = self.extract_text_accessibility()
        
        # If accessibility is empty or very short, fallback to OCR
        if len(text) < 50:
            text = self.extract_text_ocr()

        return {
            "text": text,
            "app_name": info.get("app_name", "unknown"),
            "window_title": info.get("app_name", "unknown") # Simplified
        }
