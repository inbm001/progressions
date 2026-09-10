"""오류가 남은 곡을 모두 제외 목록에 넣는다.

usage: drop_bad.py
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
RV = DATA / "review.json"


def main():
    d = json.loads(RV.read_text(encoding="utf-8"))
    drop = set(d.get("dropped", []))
    ok = set(d.get("confirmed", []))

    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    added = []
    for s in idx["songs"]:
        if s["id"] in drop or not s["unsure"]:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        left = [x for x in rec["progression"]
                if x.get("unsure")
                and f"{s['id']}:{x['at']:.2f}" not in ok]
        if left:
            drop.add(s["id"])
            added.append(s["song"] or s["title"])

    d["dropped"] = sorted(drop)
    RV.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                  encoding="utf-8")

    print(f"{len(added)}곡 제외")
    for t in added:
        print(f"  {t[:60]}")
    print(f"\n제외 합계 {len(drop)}곡")


if __name__ == "__main__":
    main()
