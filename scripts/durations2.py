"""4fps 프레임에서 코드 지속 구간을 낸다. dedup으로 OCR 대상을 줄이고,
버린 프레임은 앞 프레임의 코드를 그대로 잇는다(같은 화면이므로).
"""
import os, re, sys, time
from pathlib import Path
import numpy as np
from PIL import Image

os.environ["OMP_NUM_THREADS"] = "1"
FPS = 4
RUN = Path(r"D:\claude\chord-progression-collecting\run2")
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


def dhash(p, size=16):
    a = np.asarray(Image.open(p).convert("L").resize((size + 1, size), Image.LANCZOS), int)
    return (a[:, 1:] > a[:, :-1]).tobytes()


frames = sorted((RUN / vid).glob("f_*.jpg"))

# dedup: 화면이 바뀐 프레임만 OCR 대상
t0 = time.perf_counter()
todo, prev = [], None
for f in frames:
    h = dhash(f)
    if h != prev:
        todo.append(f)
    prev = h
t_dd = time.perf_counter() - t0
print(f"dedup: {len(frames)} -> {len(todo)} ({len(todo)/len(frames)*100:.0f}%) in {t_dd:.1f}s")

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
t0 = time.perf_counter()
text = {}
for f in todo:
    r, _ = ocr(str(f))
    text[f.name] = normalize(" ".join(x[1] for x in r) if r else "")
t_ocr = time.perf_counter() - t0
print(f"ocr: {len(todo)} frames in {t_ocr:.1f}s ({t_ocr/len(todo)*1000:.0f}ms each)\n")

# 버린 프레임은 직전 값 유지
runs, cur = [], None
for f in frames:
    idx = int(f.stem.split("_")[1]) - 1
    if f.name in text:
        cur = text[f.name]
    if runs and runs[-1]["chord"] == cur:
        runs[-1]["end"] = idx
    else:
        runs.append({"chord": cur, "start": idx, "end": idx})

print(f"{len(runs)} runs")
for r in runs:
    n = r["end"] - r["start"] + 1
    dur = n / FPS
    t = r["start"] / FPS
    print(f"  {t:5.2f}s  {dur:4.2f}s  {'#'*n:<16} {r['chord']}")

from collections import Counter
h = Counter(round((r['end']-r['start']+1)/FPS, 2) for r in runs)
print("\nduration histogram:", dict(sorted(h.items())))
