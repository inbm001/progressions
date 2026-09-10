"""남은 불확실을 곡별로 낸다. 그 곡의 진행 전체와 함께.

앞뒤 코드가 있어야 무엇이 맞는지 판단할 수 있다.

usage: remaining.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"
SITE = "http://localhost:8911/#admin/"


def main():
    p = DATA / "review.json"
    drop, ok = set(), set()
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        drop = set(d.get("dropped", []))
        ok = set(d.get("confirmed", []))

    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    rows = []
    for s in idx["songs"]:
        if s["id"] in drop:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        bad = [x for x in rec["progression"]
               if x.get("unsure")
               and f"{s['id']}:{x['at']:.2f}" not in ok]
        if bad:
            rows.append((len(bad), s, rec, bad))

    rows.sort(key=lambda r: -r[0])
    tot = sum(r[0] for r in rows)
    print(f"남은 불확실 {tot}개 · {len(rows)}곡")
    print("=" * 78)

    for n, s, rec, bad in rows:
        print()
        print(f"{(s['song'] or s['title'])[:50]}   [{n}개]")
        print(f"{SITE}{s['id']}")
        print(f"조성 {rec.get('key')}   길이 {rec.get('duration_sec')}초")
        print("-" * 78)

        badset = {x["at"] for x in bad}
        for x in rec["progression"]:
            mark = ">>" if x["at"] in badset else "  "
            shown = x.get("std") or x["chord"]
            raw = x["chord"]
            line = f"{mark} {x['at']:>6.2f} {x['dur']:>5.2f}  {shown:<22}"
            if raw != shown:
                line += f"  <- {raw!r}"
            print(line)


if __name__ == "__main__":
    main()
