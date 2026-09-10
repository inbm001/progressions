"""불확실 표기를 유형별로 묶어, 한 규칙으로 몇 곡이 풀리는지 보여준다.

원문에서 되풀이되는 꼴을 찾아 건수 순으로 낸다.

usage: patterns.py [보여줄 유형 수]
"""
import sys, json, re
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"


def load_review():
    p = DATA / "review.json"
    if not p.exists():
        return set(), set()
    d = json.loads(p.read_text(encoding="utf-8"))
    return set(d.get("dropped", [])), set(d.get("confirmed", []))


def shape(raw):
    """원문에서 되풀이되는 꼴만 남긴다. 근음과 숫자는 자리표시로 바꾼다."""
    s = re.sub(r"^[A-G][#b]?", "@", raw)      # 근음
    s = re.sub(r"\d+", "N", s)                # 숫자
    return s.strip()


def main(top=14):
    drop, ok = load_review()
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))

    kinds = Counter()
    songs_of = defaultdict(set)
    sample = {}

    for s in idx["songs"]:
        if s["id"] in drop or not s["unsure"]:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        for p in rec["progression"]:
            if not p.get("unsure"):
                continue
            if f"{s['id']}:{p['at']:.2f}" in ok:
                continue
            k = shape(p["chord"])
            kinds[k] += 1
            songs_of[k].add(s["id"])
            if k not in sample:
                sample[k] = (p["chord"], p.get("std"),
                             s["song"] or s["title"], s["id"], p["at"])

    tot = sum(kinds.values())
    print(f"불확실 {tot}개 · {len(set().union(*songs_of.values()))}곡\n")

    for k, n in kinds.most_common(top):
        raw, std, title, vid, at = sample[k]
        ns = len(songs_of[k])
        print(f"{n:>3}개 · {ns:>3}곡   {k}")
        print(f"            {raw!r} -> {std!r}")
        print(f"            {title[:40]}  https://youtu.be/{vid}")
        print()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
