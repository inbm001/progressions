"""OCR 입력 크기를 줄여 속도가 얼마나 붙는지 잰다. 정확도도 함께 본다."""
import os, time, re
from pathlib import Path
from PIL import Image

os.environ["OMP_NUM_THREADS"] = "1"
SRC = Path(r"D:\claude\chord-progression-collecting\run2\Ggnq80BOWOQ")
TMP = Path(r"C:\Users\inbm\AppData\Local\Temp\claude\D--claude-chord-progression-collecting\d394c6ca-3fc6-446f-974d-9802ed4d431f\scratchpad\croptest")

frames = sorted(SRC.glob("f_*.jpg"))[:60]
print(f"source: {len(frames)} frames, size={Image.open(frames[0]).size}")

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

VARIANTS = {
    "orig_720w":      lambda im: im,
    "left60_720w":    lambda im: im.crop((0, 0, int(im.width * .6), im.height)),
    "left60_432w":    lambda im: im.crop((0, 0, int(im.width * .6), im.height)),
    "left60_half":    lambda im: im.crop((0, 0, int(im.width * .6), im.height)).resize(
                                    (int(im.width * .3), im.height // 2), Image.LANCZOS),
}

for name, fn in VARIANTS.items():
    d = TMP / name
    d.mkdir(parents=True, exist_ok=True)
    for f in frames:
        fn(Image.open(f)).save(d / f.name, quality=90)
    sz = Image.open(next(d.glob("*.jpg"))).size

    t0 = time.perf_counter()
    texts = []
    for f in sorted(d.glob("*.jpg")):
        r, _ = ocr(str(f))
        texts.append(" ".join(x[1] for x in r) if r else "")
    el = time.perf_counter() - t0
    nonempty = sum(1 for t in texts if t.strip())
    print(f"{name:16} size={str(sz):12} {el:6.1f}s  {el/len(frames)*1000:5.0f}ms/f  "
          f"text={nonempty}/{len(frames)}")
    print(f"    sample: {texts[8]!r} {texts[20]!r} {texts[40]!r}")
