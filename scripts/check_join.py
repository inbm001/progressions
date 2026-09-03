"""조각 정렬 수정이 실제로 판독을 바로잡는지 확인한다.

usage: check_join.py <videoId>
      crop_out/<vid>_scaled/ 의 프레임을 정렬 전후로 비교한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect

ROOT = Path(r"D:\claude\chord-progression-collecting")


def main(vid):
    d = ROOT / "crop_out" / f"{vid}_scaled"
    frames = sorted(d.glob("c_*.jpg"))
    if not frames:
        print(f"{vid}: no crops — run dump_crop.py first")
        return

    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()

    n_old = n_new = 0
    for f in frames:
        r, _ = eng(str(f))
        old = " ".join(x[1] for x in r) if r else ""
        new = collect.join_boxes(r)
        o = collect.normalize(old)
        n = collect.normalize(new)
        n_old += 1 if o else 0
        n_new += 1 if n else 0
        mark = "  " if o == n else "->"
        print(f"{mark} {f.name}: {old!r} => {o!r}")
        if o != n:
            print(f"     정렬후: {new!r} => {n!r}")

    t = len(frames)
    print(f"\n정렬 전 {n_old}/{t} = {n_old/t:.0%}")
    print(f"정렬 후 {n_new}/{t} = {n_new/t:.0%}")


if __name__ == "__main__":
    main(sys.argv[1])
