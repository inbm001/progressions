"""검출(det)을 끄고 인식(rec)만 돌렸을 때의 속도·정확도.

코드 심볼은 항상 같은 위치의 한 줄이므로 검출이 불필요할 수 있다.
"""
import os, time
from pathlib import Path
from PIL import Image

os.environ["OMP_NUM_THREADS"] = "1"
SRC = Path(r"D:\claude\chord-progression-collecting\run2\Ggnq80BOWOQ")
frames = sorted(SRC.glob("f_*.jpg"))[:60]

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

# 1) 기본 (det + cls + rec)
t0 = time.perf_counter()
base = []
for f in frames:
    r, _ = ocr(str(f))
    base.append(" ".join(x[1] for x in r) if r else "")
t_base = time.perf_counter() - t0
print(f"det+cls+rec : {t_base:6.1f}s {t_base/len(frames)*1000:5.0f}ms/f")

# 2) cls 끄기
t0 = time.perf_counter()
for f in frames:
    ocr(str(f), use_cls=False)
t2 = time.perf_counter() - t0
print(f"det+rec     : {t2:6.1f}s {t2/len(frames)*1000:5.0f}ms/f")

# 3) det 끄기 — 이미지 전체를 한 줄로 간주
t0 = time.perf_counter()
recs = []
for f in frames:
    r, _ = ocr(str(f), use_det=False, use_cls=False)
    recs.append(" ".join(x[0] for x in r) if r else "")
t3 = time.perf_counter() - t0
print(f"rec only    : {t3:6.1f}s {t3/len(frames)*1000:5.0f}ms/f")

same = sum(1 for a, b in zip(base, recs) if a.strip() == b.strip())
print(f"\nrec-only matches baseline: {same}/{len(frames)}")
for i in (8, 20, 40):
    print(f"  [{i}] base={base[i]!r}  rec={recs[i]!r}")
