"""bench_ocr 결과의 실제 파싱 실패만 골라낸다. OCR 재실행 없이 문법만 검증."""
import re, sys

RAW = sys.stdin.read() if not sys.stdin.isatty() else open(sys.argv[1], encoding="utf-8").read()

ROOT = r"[A-G][#b♭♯]?"
# maj/min/dim/aug/sus/alt/add, 숫자, 괄호, 슬래시 베이스, no5 등
TAIL = r"(?:[A-Za-z0-9#b()/♭♯+\-°øΔ, ]*)"
PAT = re.compile(rf"^{ROOT}\s*{TAIL}$")

# OCR 흔한 오독 교정
FIX = [
    (r"\bMajl(\d)", r"Maj1\1"),   # Maj13 -> Majl3
    (r"\b1\s+13sus", "13sus"),     # "Cb 1 13sus" -> "Cb 13sus"
    (r"\|", ""),
]

# OCR 박스 순서가 뒤집힌 경우: "min9(11) G" -> "G min9(11)"
SWAP = re.compile(rf"^(.+?)\s+({ROOT})$")

def clean(s):
    for a, b in FIX:
        s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()

total = ok = 0
fails = []
for line in RAW.splitlines():
    if "->" not in line or ":" not in line:
        continue
    body = line.split(":", 1)[1]
    for c in body.split("->"):
        c = clean(c.strip().lstrip("?"))
        if not c:
            continue
        total += 1
        if PAT.match(c):
            ok += 1
            continue
        m = SWAP.match(c)          # 루트가 뒤로 밀린 경우 복구
        if m and PAT.match(f"{m.group(2)} {m.group(1)}"):
            ok += 1
            continue
        fails.append(c)

print(f"parse ok: {ok}/{total} = {ok/total*100:.1f}%")
print(f"failures ({len(fails)}):")
for f in sorted(set(fails)):
    print("  ", repr(f))
