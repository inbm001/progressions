"""조성 판정과 오자 수정을 답이 정해진 입력으로 시험한다."""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import detect_key, split_chord, fix_typos, looks_odd

ROOT = Path(r"D:\claude\chord-progression-collecting")


def build(chords):
    """(코드, 길이) 목록을 진행으로 바꾼다."""
    prog, t = [], 0.0
    for c, d in chords:
        fixed, _ = fix_typos(c)
        it = {"chord": c, "at": t, "dur": d}
        it.update(split_chord(fixed))
        prog.append(it)
        t += d
    return prog


print("=== 조성 판정")

CASES = [
    ("Brandy — Bb 마이너로 옮긴 커버", "Bb minor", [
        ("Bb min9", 2.5), ("Gb Maj7", 0.5), ("Cb 13sus", 3.0),
        ("Bb min7", 2.25), ("F 7(#9#5)", 2.5), ("Bb 9sus4", 2.25),
        ("Db 9(13)", 1.75), ("Bb min7", 2.75), ("Eb 13sus", 5.25),
        ("Ab 9sus4", 1.25), ("Db 9", 1.5), ("F 7#5", 1.0),
    ]),
    ("Don Blackman — A 도리안/마이너", "A", [
        ("A 9(13)#11", 2.5), ("A 7(b9b5b13)", 2.25), ("G 13sus", 2.5),
        ("E min7(11)", 2.25), ("A 9(13)#11", 2.5), ("A 7alt", 2.0),
        ("G 13sus", 2.5), ("E min9(11)", 1.5),
    ]),
    ("Gran Turismo — D 마이너", "D minor", [
        ("D 9sus4", 2.75), ("Bb min9(13)", 1.0), ("C min9(13)", 1.25),
        ("E min9(11)", 3.0), ("G min9(11)", 1.0), ("A 7(#9#5)", 1.75),
        ("D min9(11)", 2.5), ("Bb min9(11)", 1.0), ("C min9(11)", 1.5),
    ]),
]

for name, expect, chords in CASES:
    prog = build(chords)
    key, conf = detect_key(prog)
    mark = "o" if expect.split()[0] in (key or "") else "?"
    print(f"  {mark}  {name}")
    print(f"     판정 {key!r}  확신 {conf}   기대 {expect}")

print("\n=== 오자 수정")

TYPO_CASES = [
    ("Gb Mai7",         "Gb Maj7"),
    ("A Mai(b5) / Eb",  "A Maj(b5) / Eb"),
    ("Eb minor 7th",    "Eb min7"),
    ("F 7#9( (no5)",    "F 7#9(no5)"),
    ("Bb min7",         "Bb min7"),
    ("D 9sus4",         "D 9sus4"),
]
for raw, want in TYPO_CASES:
    got, sure = fix_typos(raw)
    mark = "o" if got == want else "X"
    print(f"  {mark}  {raw!r:22} -> {got!r}" +
          ("" if got == want else f"   기대 {want!r}"))

print("\n=== 물음표 붙는지")

WANT_Q = {
    # 아래 셋은 규칙으로 고쳐져 이제 물음표가 안 붙는다
    "Cb 7#5 5/ A":    False,
    "A9 9( #11)":     False,
    "Eb Perfect 5th": False,   # 음정 표기는 오류가 아니다
    "Bb min7":        False,   # 정상
    "Eb 9(13)":       False,   # 정상 변환
    "D 9sus4":        False,
    "F 7(#9#5)":      False,
    "Db Maj(add2) / F": False,
    "Ab Maj(no3)9(#11)": False,   # 생략 표시는 정상
    "Ab 7(no3) / Gb":    False,
    "F 7#9( (no5)":      False,
}
bad = 0
for raw, want in WANT_Q.items():
    fixed, sure = fix_typos(raw)
    std = split_chord(fixed).get("std") or ""
    got = looks_odd(std) or not sure
    ok = got == want
    bad += 0 if ok else 1
    print(f"  {'o' if ok else 'X'} {'?' if got else ' '}  "
          f"{raw!r:20} -> {std!r}")
print(f"\n틀림 {bad}")
