"""표준 표기 변환을 답이 정해진 입력으로 시험한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import split_chord

CASES = [
    # (화면 표기, 기대하는 표준 표기)
    ("A 9(13)#11",   "A13(#11)"),
    ("E min7(11)",   "Emin11"),
    ("G 13sus",      "G13sus"),
    ("A 7alt",       "A7alt"),
    ("A 7(b9b5b13)", "A7(b9b5b13)"),
    ("D 9sus4",      "D9sus4"),
    ("Bb min9(13)",  "Bbmin13"),
    ("C min9(13)",   "Cmin13"),
    ("A 7(#9#5)",    "A7(#9#5)"),
    ("Db Maj(add2) / F", None),      # add2 는 규칙 밖. 어떻게 나오는지 본다
    ("Cb Maj7",      "CbMaj7"),
    ("D dim7",       "Ddim7"),
    ("F min7b5(b13)", None),
    ("Gb",           "Gb"),
    ("Cb N.C.",      None),
]

ok = bad = 0
for raw, want in CASES:
    got = split_chord(raw)["std"]
    if want is None:
        print(f"  ?  {raw!r:22} -> {got!r}")
    elif got == want:
        ok += 1
        print(f"  o  {raw!r:22} -> {got!r}")
    else:
        bad += 1
        print(f"  X  {raw!r:22} -> {got!r}   기대: {want!r}")

print(f"\n맞음 {ok} / 틀림 {bad}")
