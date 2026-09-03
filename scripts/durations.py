"""기존 프레임을 다시 OCR해 각 코드의 지속 구간(초)을 낸다.

프레임 f_NNN.jpg 의 NNN 이 곧 초. 같은 코드가 연속된 구간의 길이가 지속 시간.
"""
import os, re, sys, json
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"

RUN = Path(r"D:\claude\chord-progression-collecting\run")
vid = sys.argv[1]

RT   = r"[A-G][#b♭♯]?"
TAIL = r"[A-Za-z0-9#b()/♭♯+\-°øΔ, .]*"
PAT  = re.compile(rf"^{RT}\s*{TAIL}$")
SWAP = re.compile(rf"^(.+?)\s+({RT})$")
FIXES = [(r"\|", ""), (r"\bMajl", "Maj1"), (r"\bminl", "min1"),
         (rf"^({RT})\s+1\s+(?=\d)", r"\1 "), (r"\s+", " ")]


def normalize(s):
    for a, b in FIXES:
        s = re.sub(a, b, s)
    s = s.strip()
    if not s:
        return None
    if PAT.match(s):
        return s
    m = SWAP.match(s)
    if m:
        c = f"{m.group(2)} {m.group(1)}"
        if PAT.match(c):
            return c
    return None


from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

frames = sorted((RUN / vid).glob("f_*.jpg"))
seq = []
for f in frames:
    sec = int(f.stem.split("_")[1])          # 프레임 번호 = 초
    r, _ = ocr(str(f))
    raw = " ".join(x[1] for x in r) if r else ""
    seq.append((sec, normalize(raw), raw))

# 연속 동일 코드를 구간으로 묶는다
runs = []
for sec, c, raw in seq:
    if runs and runs[-1]["chord"] == c:
        runs[-1]["end"] = sec
    else:
        runs.append({"chord": c, "start": sec, "end": sec, "raw": raw})

print(f"{vid}: {len(frames)} frames -> {len(runs)} runs\n")
for r in runs:
    dur = r["end"] - r["start"] + 1
    name = r["chord"] or f"?{r['raw']}"
    bar = "#" * dur
    print(f"  {r['start']:3d}s  {dur}s  {bar:<8} {name}")

durs = [r["end"] - r["start"] + 1 for r in runs]
from collections import Counter
print("\nduration histogram:", dict(sorted(Counter(durs).items())))
