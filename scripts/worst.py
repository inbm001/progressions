"""오류가 심한 곡을 뽑는다.

usage: worst.py [개수]
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


def load_review():
    """제외한 곡과 맞다고 확인한 코드를 읽는다."""
    p = DATA / "review.json"
    if not p.exists():
        return set(), set()
    d = json.loads(p.read_text(encoding="utf-8"))
    return set(d.get("dropped", [])), set(d.get("confirmed", []))


def main(n=12):
    drop, ok = load_review()
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))

    songs = []
    for s in idx["songs"]:
        if s["id"] in drop:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        bad = [p for p in rec["progression"]
               if p.get("unsure")
               and f"{s['id']}:{p['at']:.2f}" not in ok]
        if bad:
            s = dict(s, unsure=len(bad), _bad=bad)
            songs.append(s)

    songs.sort(key=lambda s: (-(s["unsure"] / (s["n"] or 1)), -s["unsure"]))

    print(f"제외 {len(drop)}곡 · 확인 {len(ok)}개를 뺀 뒤")
    print(f"오류 있는 곡 {len(songs)}개 중 상위 {min(n, len(songs))}개\n")
    for s in songs[:n]:
        pct = s["unsure"] / (s["n"] or 1)
        print(f"{s['unsure']:>3}/{s['n']:<3} {pct:>4.0%}  "
              f"{(s['song'] or s['title'])[:38]:<38} "
              f"{(s['artist'] or '')[:20]}")
        bad = s["_bad"]
        seen = []
        for p in bad:
            t = f"{p['chord']!r} -> {p.get('std')!r}"
            if t not in seen:
                seen.append(t)
        for t in seen[:4]:
            print(f"           {t}")
        print(f"           https://youtu.be/{s['id']}")
        print()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
