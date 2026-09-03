"""bench/ 의 모든 크롭을 OCR하고, 코드 심볼 파싱 성공률을 잰다."""
import re, time, json
from pathlib import Path
from collections import OrderedDict
import concurrent.futures as cf

BENCH = Path(r"D:\claude\chord-progression-collecting\bench")

# 코드 심볼 문법. OCR이 붙이는 '|' 나 공백은 미리 제거한다.
ROOT = r"[A-G](?:#|b|♭|♯)?"
QUAL = r"(?:maj|min|m|M|dim|aug|sus|alt|add|°|ø|Δ|-|\+|\d|[#b()/,]|\s)*"
PAT = re.compile(rf"^({ROOT})({QUAL})$")

def norm(s):
    s = s.replace("|", "").replace("１", "1").replace("０", "0")
    s = re.sub(r"\s+", " ", s).strip()
    return s

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

vids = sorted(d for d in BENCH.iterdir() if d.is_dir())
t0 = time.perf_counter()

total, parsed, out = 0, 0, {}
for d in vids:
    seq = []
    for f in sorted(d.glob("f_*.jpg")):
        res, _ = ocr(str(f))
        txt = norm(" ".join(r[1] for r in res)) if res else ""
        total += 1
        if txt and PAT.match(txt):
            parsed += 1
            seq.append(txt)
        elif txt:
            seq.append("?" + txt)
    # 연속 중복 제거
    prog = [c for i, c in enumerate(seq) if i == 0 or c != seq[i-1]]
    out[d.name] = prog
    print(f"{d.name}: {' -> '.join(prog)}")

el = time.perf_counter() - t0
print(f"\n[ocr] {total} frames in {el:.1f}s ({el/total*1000:.0f}ms each)")
print(f"  parse ok: {parsed}/{total} = {parsed/total*100:.1f}%")
print(f"  projected 1478 vids (~33 frames avg): {el/total*33*1478/60:.1f} min single-thread")
