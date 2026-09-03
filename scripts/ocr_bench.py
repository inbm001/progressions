"""코드 심볼 영역만 잘라 OCR하고, 속도와 결과를 측정한다.

코드 심볼 영역: y=722..788 (건반 위, 흰 배경 + 검은 글씨)
"""
import sys, time
from pathlib import Path
from PIL import Image

Y0, Y1 = 720, 790

frames = sorted(Path(sys.argv[1]).glob("*.jpg"))
crop_dir = Path(sys.argv[1]).parent / "crops"
crop_dir.mkdir(exist_ok=True)

t0 = time.perf_counter()
crops = []
for f in frames:
    im = Image.open(f).crop((0, Y0, 720, Y1))
    p = crop_dir / f.name
    im.save(p)
    crops.append(p)
t_crop = time.perf_counter() - t0
print(f"crop: {len(crops)} frames in {t_crop:.2f}s ({t_crop/len(crops)*1000:.0f}ms each)")

from rapidocr_onnxruntime import RapidOCR
t0 = time.perf_counter()
ocr = RapidOCR()
print(f"engine init: {time.perf_counter()-t0:.2f}s")

t0 = time.perf_counter()
for p in crops:
    res, _ = ocr(str(p))
    txt = " | ".join(r[1] for r in res) if res else "(none)"
    print(f"{p.name}: {txt}")
t_ocr = time.perf_counter() - t0
print(f"\nocr: {len(crops)} crops in {t_ocr:.2f}s ({t_ocr/len(crops)*1000:.0f}ms each)")
