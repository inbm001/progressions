"""오자 규칙이 한 단계씩 무엇을 바꾸는지 본다.

usage: trace.py "원문"
"""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import TYPOS, FIXES, split_chord

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main(s):
    print(f"원문   {s!r}")
    cur = s
    for pat, rep, ok in TYPOS:
        new = re.sub(pat, rep, cur)
        if new != cur:
            print(f"  TYPO {pat!r}")
            print(f"       {cur!r} -> {new!r}")
            cur = new
    for a, b in FIXES:
        new = re.sub(a, b, cur)
        if new != cur:
            print(f"  FIX  {a!r}")
            print(f"       {cur!r} -> {new!r}")
            cur = new
    print(f"결과   {cur!r}")
    print(f"표준   {split_chord(cur).get('std')!r}")


if __name__ == "__main__":
    main(sys.argv[1])
