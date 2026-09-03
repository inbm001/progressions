"""빠른 경로 결과가 기존(느린) 결과와 같은 진행을 내는지 비교한다."""
import json
from pathlib import Path

OUT = Path(r"D:\claude\chord-progression-collecting\out")
old = {r["id"]: r for r in json.loads((OUT / "chords_baseline5.json").read_text(encoding="utf-8"))}
new = {r["id"]: r for r in json.loads((OUT / "chords.json").read_text(encoding="utf-8"))}

print(f"old={len(old)} new={len(new)}\n")
for vid in new:
    n = new[vid]
    o = old.get(vid)
    ns = [c["chord"] for c in n["progression"]]
    print(f"{vid}  slow_recheck={n.get('n_slow','-')}/{n['n_ocr']}  rate={n['ocr_rate']:.0%}  {n['title'][:45]}")
    if o is None:
        print("   (no baseline)")
        continue
    os_ = [c["chord"] for c in o["progression"]]
    if ns == os_:
        print(f"   IDENTICAL ({len(ns)} chords)")
    else:
        print(f"   DIFF  old={len(os_)} new={len(ns)}")
        for i in range(max(len(os_), len(ns))):
            a = os_[i] if i < len(os_) else "-"
            b = ns[i] if i < len(ns) else "-"
            if a != b:
                print(f"     [{i}] old={a!r}  new={b!r}")
