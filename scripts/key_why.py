"""조성이 애매한 이유를 유형별로 센다.

1등과 2등 조성이 어떤 관계인지 보면 원인이 갈린다.
  - 나란한조 (Am / C)      : 장단조가 안 갈림
  - 같은으뜸음조 (Am / A)  : 3음이 흔들림
  - 5도 관계 (Am / Em)     : 도리안·믹솔리디안
  - 그 밖                  : 전조이거나 판독 문제

usage: key_why.py
"""
import sys, json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import (ROOT, MAJOR_SET, MINOR_SET, chord_tones,
                     NAMES_FLAT, NAMES_SHARP)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"


def rank_keys(prog):
    """조성 후보를 점수순으로 돌려준다. detect_key 와 같은 계산."""
    weight = [0.0] * 12
    root_w = [0.0] * 12
    for p in prog:
        pc = p.get("pc")
        if pc is None:
            continue
        d = float(p.get("dur") or 0.25)
        root_w[pc] += d
        for t in chord_tones(pc, p.get("quality")):
            weight[t] += d

    total = sum(weight)
    if total <= 0:
        return []

    pcs = [p.get("pc") for p in prog if p.get("pc") is not None]
    first_pc = pcs[0] if pcs else None
    last_pc = pcs[-1] if pcs else None
    rw_total = sum(root_w) or 1.0
    longest_pc = max(range(12), key=lambda i: root_w[i])

    out = []
    for tonic in range(12):
        for is_minor, scale in ((0, MAJOR_SET), (1, MINOR_SET)):
            inside = sum(weight[(tonic + s) % 12] for s in scale)
            score = inside / total
            score += 0.30 * (root_w[tonic] / rw_total)
            score += 0.10 * (root_w[(tonic + 7) % 12] / rw_total)
            if tonic == first_pc:
                score += 0.12
            if tonic == last_pc:
                score += 0.08
            if tonic == longest_pc:
                score += 0.12
            out.append((score, tonic, is_minor))
    out.sort(reverse=True)
    return out


def relation(a, b):
    """1등과 2등의 관계를 이름 붙인다."""
    _, t1, m1 = a
    _, t2, m2 = b
    d = (t2 - t1) % 12
    if m1 != m2:
        if (m1 == 1 and d == 3) or (m1 == 0 and d == 9):
            return "나란한조"          # Am / C
        if d == 0:
            return "같은으뜸음조"      # Am / A
        return "장단 다름"
    if d in (7, 5):
        return "5도 관계"              # Am / Em
    if d == 2:
        return "2도 관계"
    return "그 밖"


def main():
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    low = [s for s in idx["songs"] if s["conf"] < 0.5]

    kinds = Counter()
    samples = {}
    for s in low:
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        r = rank_keys(rec["progression"])
        if len(r) < 2:
            continue
        k = relation(r[0], r[1])
        kinds[k] += 1
        if k not in samples:
            names = NAMES_FLAT
            n1 = names[r[0][1]] + (" minor" if r[0][2] else " major")
            n2 = names[r[1][1]] + (" minor" if r[1][2] else " major")
            samples[k] = (s["song"] or s["title"], n1, n2,
                          round(r[0][0] - r[1][0], 3))

    print(f"확신 낮은 곡 {len(low)}개의 원인\n")
    for k, n in kinds.most_common():
        t, n1, n2, gap = samples[k]
        print(f"{n:>4}  {k}")
        print(f"      예: {t[:34]:<34} {n1} vs {n2} (차 {gap})")
    print()


if __name__ == "__main__":
    main()
