"""looks_odd 가 무엇을 보고 판단하는지 값을 그대로 덤프한다."""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import split_chord, fix_typos, RT

CASES = [
    ("Cb 7#5 5/ A",      True),
    ("A9 9( #11)",       True),
    ("Eb Perfect 5th",   True),
    ("Bb min7",          False),
    ("Eb 9(13)",         False),
    ("D 9sus4",          False),
    ("F 7(#9#5)",        False),
    ("Db Maj(add2) / F", False),
    ("G 13sus",          False),
    ("Bb min7(4)",       False),
    ("A Maj7b5",         False),
]

print(f"{'원문':22} {'std':20} {'tail':14} {'nums':14} {'기대'}")
for raw, want in CASES:
    fixed, sure = fix_typos(raw)
    std = split_chord(fixed).get("std") or ""
    tail = re.sub(rf"^{RT}", "", std)
    stripped = re.sub(r"\([^)]*\)", "", tail)
    nums = re.findall(r"\d+", stripped)
    print(f"{raw!r:22} {std!r:20} {stripped!r:14} {str(nums):14} "
          f"{'?' if want else '-'}  sure={sure}")
