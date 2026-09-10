"""근음만 남은 곡을 찾는다.

코드 화면이 없는 영상에서 다른 글자를 읽으면, 자막을 뗀 뒤 근음만 남는다.
'Cwws' -> 'C', 'FREO' -> 'F' 같은 것.

usage: bare_roots.py
"""
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import ROOT, RT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"


def main():
    p = DATA / "review.json"
    drop = set()
    if p.exists():
        drop = set(json.loads(p.read_text(encoding="utf-8")).get("dropped", []))

    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    rows = []
    for s in idx["songs"]:
        if s["id"] in drop:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        prog = rec["progression"]
        if not prog:
            continue
        bare = sum(1 for x in prog
                   if re.fullmatch(RT, (x.get("std") or "").strip()))
        if bare / len(prog) >= 0.7:
            rows.append((bare / len(prog), bare, len(prog),
                         s["song"] or s["title"], s["id"]))

    rows.sort(reverse=True)
    print(f"근음만 남은 곡 {len(rows)}개\n")
    for pct, bare, tot, title, vid in rows:
        print(f"{bare:>3}/{tot:<3} {pct:>4.0%}  {title[:40]:<40} {vid}")

    print()
    print("제외 목록에 넣을 id")
    print(json.dumps([r[4] for r in rows], indent=2))


if __name__ == "__main__":
    main()
