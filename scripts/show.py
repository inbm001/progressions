import json, sys
from pathlib import Path

d = json.loads(Path(r"D:\claude\chord-progression-collecting\out\chords.json").read_text(encoding="utf-8"))
for r in d:
    p = r["progression"]
    print(f"{r['id']}  n={len(p):3d}  {r['title'][:55]}")
    print(f"    {' -> '.join(p[:10])}")
print(f"\ntotal videos: {len(d)}")
print(f"empty: {sum(1 for r in d if not r['progression'])}")
