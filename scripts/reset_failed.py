"""실패한 곡의 결과를 지워 다음 실행에서 다시 처리하게 한다.

usage: reset_failed.py [사유 ...]
      사유를 주지 않으면 no_frames 만 지운다.
      예: reset_failed.py no_frames failed_low_ocr
"""
import sys, json
from pathlib import Path

ROOT = Path(r"D:\claude\chord-progression-collecting")
DONE = ROOT / "done"


def main(reasons):
    if not reasons:
        reasons = ["no_frames"]
    reasons = set(reasons)

    n = 0
    kept = {}
    for p in sorted(DONE.glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        st = r.get("status")
        if st in reasons:
            p.unlink()
            n += 1
        else:
            kept[st] = kept.get(st, 0) + 1

    print(f"지운 곡 {n}")
    for k, v in sorted(kept.items()):
        print(f"  남김 {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1:])
