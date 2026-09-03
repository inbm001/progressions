"""여백을 잘라낸 뒤 rec-only OCR의 정확도를 잰다.

코드 심볼은 흰 배경 위 검은 글씨. 어두운 픽셀이 있는 열의 범위로 자른다.
"""
import os, time
from pathlib import Path
import numpy as np
from PIL import Image

os.environ["OMP_NUM_THREADS"] = "1"
SRC = Path(r"D:\claude\chord-progression-collecting\run2\Ggnq80BOWOQ")
frames = sorted(SRC.glob("f_*.jpg"))[:60]

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()


def trim(path, pad=6, thr=128):
    """글자가 있는 x 구간만 남긴다. 글자가 없으면 None."""
    im = Image.open(path).convert("L")
    a = np.asarray(im, dtype=int)
    dark = (a < thr).sum(axis=0)          # 열별 어두운 픽셀 수
    cols = np.nonzero(dark >= 2)[0]
    if len(cols) == 0:
        return None
    x0 = max(0, cols[0] - pad)
    x1 = min(a.shape[1], cols[-1] + pad + 1)
    return im.crop((x0, 0, x1, im.height))


# 기준선
t0 = time.perf_counter()
base = []
for f in frames:
    r, _ = ocr(str(f))
    base.append(" ".join(x[1] for x in r) if r else "")
t_base = time.perf_counter() - t0
print(f"baseline (det+cls+rec): {t_base:.1f}s  {t_base/len(frames)*1000:.0f}ms/f")

TMP = Path(os.environ["TEMP"]) / "trimtest"
TMP.mkdir(exist_ok=True)

t0 = time.perf_counter()
recs, widths = [], []
for f in frames:
    im = trim(f)
    if im is None:
        recs.append("")
        continue
    widths.append(im.width)
    p = TMP / f.name
    im.save(p, quality=95)
    r, _ = ocr(str(p), use_det=False, use_cls=False)
    recs.append(" ".join(x[0] for x in r) if r else "")
t_new = time.perf_counter() - t0
print(f"trim + rec only       : {t_new:.1f}s  {t_new/len(frames)*1000:.0f}ms/f")
print(f"speedup: {t_base/t_new:.1f}x   crop widths {min(widths)}~{max(widths)}")

same = sum(1 for a, b in zip(base, recs) if a.replace(" ", "") == b.replace(" ", ""))
print(f"\nexact match (ignoring spaces): {same}/{len(frames)}")
for i, (a, b) in enumerate(zip(base, recs)):
    if a.replace(" ", "") != b.replace(" ", ""):
        print(f"  [{i:3d}] base={a!r:24} rec={b!r}")
