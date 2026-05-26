import sys
import threading
import time

BRAILLE_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class StatusLine:
    def __init__(self):
        self._text = ""
        self._running = False
        self._thread = None
        self._frame = 0
        self._lock = threading.Lock()

    def update(self, text):
        with self._lock:
            self._text = text
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()

    def complete(self, text):
        self._stop()
        sys.stderr.write(f"\r\033[K\033[32m  ✓ {text}\033[0m\n")
        sys.stderr.flush()

    def clear(self):
        self._stop()
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()

    def _stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None

    def _spin(self):
        while self._running:
            with self._lock:
                text = self._text
            frame = BRAILLE_FRAMES[self._frame % len(BRAILLE_FRAMES)]
            sys.stderr.write(f"\r\033[K\033[36m  {frame} {text}\033[0m")
            sys.stderr.flush()
            self._frame += 1
            time.sleep(0.1)
