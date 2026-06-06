import sys
import threading

MAX_LINES = 200
_buffer = []
_lock = threading.Lock()

class Capture:
    def __init__(self, original):
        self.original = original

    def write(self, text):
        with _lock:
            _buffer.append(text)
            if len(_buffer) > MAX_LINES:
                _buffer[:50] = []
        self.original.write(text)

    def flush(self):
        self.original.flush()

def get_recent(n=50):
    with _lock:
        all_lines = []
        for chunk in _buffer:
            all_lines.extend(chunk.splitlines())
        return all_lines[-n:]

def install():
    sys.stdout = Capture(sys.stdout)
