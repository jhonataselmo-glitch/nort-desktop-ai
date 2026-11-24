import getpass
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path


def redact(value):
    if isinstance(value, dict):
        return {k: ("[PROTEGIDO]" if k.lower() in {"password", "senha", "token", "api_key", "authorization", "text", "value"} else redact(v)) for k,v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"(?:gsk_|sk-)[A-Za-z0-9_-]+", "[CHAVE PROTEGIDA]", value)
    return value


class Audit:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def record(self, event, **data):
        row = dict(time=datetime.now(timezone.utc).isoformat(), user=getpass.getuser(), event=event, **redact(data))
        with self.lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            f.flush()
