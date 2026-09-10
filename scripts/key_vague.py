"""장단이 흐린 곡을 뽑는다. 진행과 함께.

으뜸음은 확실한데 장조·단조가 안 갈리는 곡. 3음을 뺀 화음이 많으면 그렇다.

usage: key_vague.py [곡 수]
"""
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import (ROOT, MODES, chord_tones, NAMES_FLAT, NAMES_SHARP)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"
SITE = "http://localhost:8911/#admin/"


def rank(prog):
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
    first_pc, last_pc = (pcs[0], pcs[-1]) if pcs else (None, None)
    rw = sum(root_w) or 1.0
    longest = max(range(12), key=lambda i: root_w[i])

    out = []
    for tonic in range(12):
        for name, scale, bias in MODES:
            inside = sum(weight[(tonic + s) % 12] for s in scale)
            sc = inside / total + bias
            sc += 0.30 * (root_w[tonic] / rw)
            sc += 0.10 * (root_w[(tonic + 7) % 12] / rw)
            if tonic == first_pc:  sc += 0.12
            if tonic == last_pc:   sc += 0.08
            if tonic == longest:   sc += 0.12
            out.append((sc, tonic, name))
    out.sort(key=lambda x: -x[0])
    return out


def main(n=6):
    p = DATA / "review.json"
    drop = set()
    if p.exists():
        drop = set(json.loads(p.read_text(encoding="utf-8")).get("dropped", []))

    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    rows = []
    for s in idx["songs"]:
        if s["id"] in drop or s["conf"] >= 0.5:
            continue
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        r = rank(rec["progression"])
        if len(r) < 2:
            continue
        # 으뜸음은 같은데 선법만 다른 것 = 장단이 흐린 곡
        if r[0][1] != r[1][1]:
            continue
        # 3음을 뺀 화음 비율
        nosus = sum(1 for x in rec["progression"]
                    if re.search(r"(sus|no3)", x.get("quality") or "", re.I))
        rows.append((nosus / len(rec["progression"]), s, rec, r))

    rows.sort(key=lambda x: -x[0])
    print(f"장단이 흐린 곡 {len(rows)}개 · 앞 {min(n, len(rows))}개\n")
    print("=" * 74)

    for pct, s, rec, r in rows[:n]:
        names = NAMES_FLAT
        cands = []
        for sc, t, nm in r[:4]:
            cands.append(f"{names[t]} {nm} ({sc:.3f})")
        print()
        print(f"{(s['song'] or s['title'])[:48]}")
        print(f"{SITE}{s['id']}")
        print(f"지금 판정 {rec.get('key')}")
        print(f"후보      {'  |  '.join(cands)}")
        print(f"3음 뺀 화음 {pct:.0%}")
        print("-" * 74)
        for x in rec["progression"][:16]:
            print(f"  {x['at']:>6.2f} {x['dur']:>5.2f}  {x.get('std') or x['chord']}")
        if len(rec["progression"]) > 16:
            print(f"  ... +{len(rec['progression']) - 16}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
