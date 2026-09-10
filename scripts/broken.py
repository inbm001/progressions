"""판독이 통째로 무너진 구간을 찾는다.

화면 자막이나 다른 글자가 코드 자리에 섞여 들어온 것.
불확실 표시가 안 붙어도 값 자체가 코드가 아닌 경우가 있다.

usage: broken.py [보여줄 곡 수]
"""
import sys, json, re
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import ROOT, RT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"

# 코드에 쓰이는 글자만 모은 것. 이것 말고 다른 낱말이 있으면 자막이다.
KNOWN = re.compile(
    r"^(Maj|maj|min|dim|aug|sus|add|alt|no|n\.c\.|N\.C\.|"
    r"Perfect|Octave|Tritone|Major|Minor|st|nd|rd|th|b|#|/|\d|\s|\(|\)|\+|-)*$",
    re.I)


def load_drop():
    p = DATA / "review.json"
    if not p.exists():
        return set()
    return set(json.loads(p.read_text(encoding="utf-8")).get("dropped", []))


def junk_words(raw):
    """코드 문법에 없는 낱말을 뽑는다."""
    tail = re.sub(rf"^{RT}", "", raw)
    if KNOWN.match(tail):
        return []
    # 두 글자 이상 이어진 영문 중 코드 낱말이 아닌 것
    out = []
    for w in re.findall(r"[A-Za-z]{2,}", tail):
        if re.fullmatch(r"(Maj|maj|min|dim|aug|sus|add|alt|no|"
                        r"Perfect|Octave|Tritone|Major|Minor|"
                        r"st|nd|rd|th)", w, re.I):
            continue
        out.append(w)
    return out


def main(top=14):
    drop = load_drop()
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))

    rows = []
    words = Counter()
    for s in idx["songs"]:
        if s["id"] in drop:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        bad = []
        for p in rec["progression"]:
            w = junk_words(p["chord"])
            if w:
                bad.append((p["chord"], p.get("std"), w))
                words.update(x.lower() for x in w)
        if bad:
            rows.append((len(bad), len(rec["progression"]),
                         s["song"] or s["title"], s["id"], bad))

    rows.sort(key=lambda r: -r[0] / (r[1] or 1))

    print(f"자막이 섞인 곡 {len(rows)}개\n")
    for n, tot, title, vid, bad in rows[:top]:
        print(f"{n:>3}/{tot:<3} {n/tot:>4.0%}  {title[:38]:<38} "
              f"https://youtu.be/{vid}")
        seen = []
        for raw, std, w in bad:
            t = f"{raw!r} -> {std!r}"
            if t not in seen:
                seen.append(t)
        for t in seen[:3]:
            print(f"            {t}")
        print()

    print("자주 섞이는 낱말")
    for w, n in words.most_common(12):
        print(f"  {n:>3}  {w}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
