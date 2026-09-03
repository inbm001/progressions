"""건반 상단 경계 주변 행을 1행 단위로 덤프한다.

usage: dump_edge.py <이미지> <중심y> [반경]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def dump(path, center, radius=40):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    h, w = a.shape
    print(f"=== {Path(path).parent.name}/{Path(path).name}  {w}x{h}  center={center}")
    print(f"{'y':>5} {'frac':>6} {'white':>6} {'dark':>6} {'mean':>6} {'std':>6} {'edges':>6}")
    for y in range(max(0, center - radius), min(h, center + radius + 1)):
        row = a[y]
        white = (row >= 200).mean()
        dark  = (row <= 100).mean()
        b = (row >= 150).astype(np.int8)
        e = int(np.abs(np.diff(b)).sum())
        print(f"{y:>5} {y/h:>6.3f} {white:>6.2f} {dark:>6.2f} "
              f"{row.mean():>6.1f} {row.std():>6.1f} {e:>6d}")
    print()


if __name__ == "__main__":
    p = sys.argv[1]
    c = int(sys.argv[2])
    r = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    dump(p, c, r)
