"""판독된 조각의 좌표와 내용을 그대로 덤프한다.

usage: dump_ocr_boxes.py <videoId>
      crop_out/<vid>_scaled/ 의 프레임을 대상으로 한다.
"""
import sys
from pathlib import Path

ROOT = Path(r"D:\claude\chord-progression-collecting")


def main(vid):
    d = ROOT / "crop_out" / f"{vid}_scaled"
    frames = sorted(d.glob("c_*.jpg"))
    if not frames:
        print(f"{vid}: no crops")
        return

    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()

    for f in frames[:6]:
        h = Image.open(f).size[1]
        r, _ = eng(str(f))
        print(f"=== {f.name}  height={h}")
        if not r:
            print("   (없음)")
            continue
        for box, txt, conf in r:
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            print(f"   y {min(ys):6.1f}-{max(ys):6.1f} "
                  f"({min(ys)/h:.2f}-{max(ys)/h:.2f}) "
                  f"x {min(xs):6.1f}  conf={conf:.2f}  {txt!r}")
        print()


if __name__ == "__main__":
    main(sys.argv[1])
