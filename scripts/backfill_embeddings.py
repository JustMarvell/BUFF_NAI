import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.memory import load_memory, _save_memory, get_embedding

entries = load_memory()
updated = 0
for e in entries:
    if not e.get("embedding"):
        e["embedding"] = get_embedding(e["text"])
        updated += 1
_save_memory(entries)
print(f"Backfilled {updated} entry(ies)")