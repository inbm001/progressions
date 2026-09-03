"""rec-only 결과의 꼬리 잡음을 제거하고 baseline과 일치하는지 검증한다."""
import re

PAIRS = [
 ('Fb min9','Fb min9nennn'),('Fb min9','Fb min9en'),('Eb min9','Ebmin9nu'),
 ('Eb min9','Ebmin9e'),('Cb / Gb','Cb / Gbun'),('Ab dim7','Abdim7eeeo'),
 ('Eb min9','Ebmin9nun'),('Eb min9','Eb min9nun'),('Eb min9','Eb min9eue'),
 ('Eb min9','Eb min9eune'),('Eb min9','Eb min9eunne'),('Ab min9','Ab min9eeee'),
 ('Bb 7(b9#5)','Bb 7(b9#5）mm-'),('Eb min9','Eb min9eunee'),('Eb min9','Ebmin9enn'),
 ('Ab min9','Abmin9eennn'),('Fb / Bb','Fb/Bbun'),('Eb min9','Eb min9nnn'),
 ('Eb min9','Ebmin9nnn'),
]

RT = r"[A-G][#b♭♯]?"
# 코드 심볼로 유효한 본문. 꼬리 잡음(e,u,n,m,o,- 반복)은 뒤에서 벗겨낸다.
TAILJUNK = re.compile(r"[eunmo\-\s]+$")
FULLWIDTH = str.maketrans("（）＃♭", "()#b")


def clean(s):
    s = s.translate(FULLWIDTH)
    s = TAILJUNK.sub("", s)
    # 괄호가 열렸는데 안 닫혔으면 닫는다
    if s.count("(") > s.count(")"):
        s += ")"
    # 루트와 나머지 사이 공백 정규화
    m = re.match(rf"^({RT})\s*(.*)$", s)
    if m:
        s = f"{m.group(1)} {m.group(2)}".strip()
    return re.sub(r"\s+", " ", s).strip()


ok = 0
for want, raw in PAIRS:
    got = clean(raw)
    hit = got.replace(" ", "") == want.replace(" ", "")
    ok += hit
    print(f"{'OK ' if hit else 'BAD'} {raw!r:22} -> {got!r:16} want {want!r}")
print(f"\n{ok}/{len(PAIRS)}")
