"""표준 표기 변환을 답이 정해진 입력으로 시험한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import split_chord, fix_typos

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
    ("Ab Maj(no3)9(#11)", "AbMaj9(#11)(no3)"),
    ("Ab 7(no3) / Gb",    "Ab7(no3)/Gb"),
    ("F 7#9( (no5)",      "F7(#9)(no5)"),
    # 사용자가 짚어 준 것
    ("F Maj99 / A",       "FMaj9/A"),
    ("F Maj9 9 / A",      "FMaj9/A"),
    ("A 9 9(#11)",        "A9(#11)"),
    # 음정 표기 — 코드가 아니라 두 음. 물음표를 붙이지 않는다.
    ("A Perfect 5th",     "A Perfect 5th"),
    ("C Octave",          "C Octave"),
    ("A min 3rd",         "A min 3rd"),
    ("B Major 3rd",       "B Major 3rd"),
    # 괄호 겹침·낀 숫자
    ("F 13sus4(c(add3)",  "F13sus4(add3)"),
    ("E Maj313(#11)",     "EMaj13(#11)"),
    # 실제 원문에는 공백이 끼어 있다
    ("F 13sus4(c (add3)", "F13sus4(add3)"),
    ("F 13sus4(o (add3)", "F13sus4(add3)"),
    ("E Maj13( 3(#11)",   "EMaj13(#11)"),
    ("D# min7(4) C#",     "D#min11/C#"),
    ("B min9 11 /A",      "Bmin11/A"),
    # 실제 데이터에서 나온 것
    ("C 113sus",          "C13sus"),
    ("C 19",              "C9"),
    ("B3 Maj7",           "BMaj7"),
    ("B3 Maj9",           "BMaj9"),
    ("B3 / F#",           "B/F#"),
    ("Ab Maj(o(add2)",    "AbMaj(add2)"),
    ("D min17",           "Dmin11"),
    ("C min19",           "Cmin9"),
    ("Db Maj#1l9(no3)",   "DbMaj9(#11)(no3)"),
    ("F Maj#19",          "FMaj9(#11)"),
    ("B mins11",          "Bmin11"),
    ("A M1aj13(add4)",    None),
    ("D min7(4)",         "Dmin11"),
    ("D min9(11)",        "Dmin11"),
    ("Ab Maj#1l9(no3)",   "AbMaj9(#11)(no3)"),
    ("Cb N.C.",      None),
]

ok = bad = 0
for raw, want in CASES:
    fixed, _ = fix_typos(raw)
    got = split_chord(fixed)["std"]
    if want is None:
        print(f"  ?  {raw!r:22} -> {got!r}")
    elif got == want:
        ok += 1
        print(f"  o  {raw!r:22} -> {got!r}")
    else:
        bad += 1
        print(f"  X  {raw!r:22} -> {got!r}   기대: {want!r}")

print(f"\n맞음 {ok} / 틀림 {bad}")
