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
            # Advanced recursive AppleScript for deep UI tree unwrapping
            script = '''
            on recurseElements(theElement, depth)
                if depth > 5 then return "" -- Limit depth for performance
                set resultText to ""
                try
                    set resultText to resultText & (value of theElement as string) & " "
                end try
                try
                    set subElements to UI elements of theElement
                    repeat with subEl in subElements
                        set resultText to resultText & my recurseElements(subEl, depth + 1)
                    end repeat
                end try
                return resultText
            end recurseElements

            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    try
                        set rootElements to UI elements
                        set totalText to ""
                        repeat with rootEl in rootElements
                            set totalText to totalText & my recurseElements(rootEl, 0)
                        end repeat
                        return totalText
                    on error
                        return ""
                    end try
                end tell
            end tell
            '''
            try:
                proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
                return proc.stdout.strip()
            except Exception as e:
                print(f"Accessibility Error: {e}")
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
