"""조성이 도중에 바뀌는지 본다.

곡을 앞뒤로 갈라 각각 조성을 짚어 본다. 다르면 전조한 것이다.

usage: key_split.py [곡수]
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import detect_key, ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = ROOT / "docs" / "data"


def halves(prog):
    """앞뒤로 갈라 각각의 조성을 돌려준다."""
    n = len(prog)
    if n < 8:
        return (None, 0.0), (None, 0.0)
    a = detect_key(prog[: n // 2])
    b = detect_key(prog[n // 2 :])
    return a, b


def main(limit=20):
    idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
    low = [s for s in idx["songs"] if s["conf"] < 0.5]

    n_shift = n_vague = 0
    shown = 0
    for s in low:
        rec = json.loads((DATA / "songs" / f"{s['id']}.json")
                         .read_text(encoding="utf-8"))
        (ka, ca), (kb, cb) = halves(rec["progression"])
        if not ka or not kb:
            continue
        # 앞뒤가 다르고 둘 다 어느 정도 확신이 있으면 전조로 본다
        shift = (ka != kb) and ca >= 0.4 and cb >= 0.4
        if shift:
            n_shift += 1
        else:
            n_vague += 1
        if shift and shown < limit:
            shown += 1
            print(f"{(s['song'] or s['title'])[:40]:<40} "
                  f"전체 {s['key']:<14} 앞 {ka}({ca}) 뒤 {kb}({cb})")

    print()
    print(f"확신 낮은 곡 {len(low)}개")
    print(f"  전조로 보이는 것   {n_shift}")
    print(f"  그냥 애매한 것     {n_vague}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
