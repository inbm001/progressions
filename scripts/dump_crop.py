"""파이프라인과 동일한 크롭을 적용해 결과 이미지를 남긴다.

usage: dump_crop.py <videoId> [--scale]
      probe/<vid>/v.* 를 써서 crop_out/<vid>/ 에 프레임을 남긴다.
      --scale 을 주면 collect.py 와 같은 scale=720:-1 을 적용한다.
"""
import sys, json, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect

ROOT   = Path(r"D:\claude\chord-progression-collecting")
PROBE  = ROOT / "probe"
OUT    = ROOT / "crop_out"
FFMPEG = collect.FFMPEG


def main(vid, scaled):
    d = PROBE / vid
    vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        print(f"{vid}: no video in probe/ — run probe_layout.py first")
        return

    top, bh, how = collect.detect_band(vf, d)
    print(f"{vid}: top={top:.4f} h={bh:.4f} ({how})")

    o = OUT / (vid + ("_scaled" if scaled else "_raw"))
    o.mkdir(parents=True, exist_ok=True)
    vfil = f"fps=1,crop=iw:ih*{bh:.6f}:0:ih*{top:.6f}"
    if scaled:
        vfil += ",scale=720:-1"
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
         "-t", "12", "-vf", vfil, "-q:v", "3", str(o / "c_%02d.jpg")],
        capture_output=True)
    print(f"  -> {o}  ({len(list(o.glob('c_*.jpg')))} frames)")


if __name__ == "__main__":
    scaled = "--scale" in sys.argv
    for v in [a for a in sys.argv[1:] if not a.startswith("--")]:
        main(v, scaled)
