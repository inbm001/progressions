"""자동 탐지한 크롭으로 실제 OCR 이 되는지 확인한다.

usage: verify_band.py <videoId> [...]
      probe/<vid>/full_*.jpg 를 탐지 크롭으로 잘라 OCR 결과를 출력한다.
"""
import sys, re
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from find_band import find_band
from collect import normalize

ROOT  = Path(r"D:\claude\chord-progression-collecting")
PROBE = ROOT / "probe"


def main(vids):
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()

    for vid in vids:
        d = PROBE / vid
        frames = sorted(d.glob("full_*.jpg"))
        if not frames:
            print(f"{vid}: no frames")
            continue

        print(f"=== {vid}  ({len(frames)} frames)")
        # 대표 프레임에서 띠 위치를 정하고 전체에 같은 값을 쓴다
        band = None
        for f in frames:
            band = find_band(f)
            if band:
                print(f"  band from {f.name}: top={band[0]:.4f} h={band[1]:.4f}")
                break
        if not band:
            print("  band not found")
            continue

        top, bh = band
        out = d / "crop"
        out.mkdir(exist_ok=True)
        n_ok = n_bad = 0
        for f in frames:
            im = Image.open(f)
            W, H = im.size
            y0 = int(H * top)
            y1 = int(H * (top + bh))
            c = im.crop((0, y0, W, y1))
            cp = out / f.name
            c.save(cp, quality=95)

            r, _ = eng(str(cp))
            raw = " ".join(x[1] for x in r) if r else ""
            norm = normalize(raw)
            if raw.strip():
                if norm:
                    n_ok += 1
                else:
                    n_bad += 1
            print(f"  {f.name}: {raw!r} -> {norm!r}")

        tot = n_ok + n_bad
        print(f"  판독률 {n_ok}/{tot} = {n_ok/tot if tot else 0:.0%}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
