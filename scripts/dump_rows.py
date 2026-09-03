"""행별 픽셀 통계를 그대로 덤프한다. 추측 대신 실측을 본다.

usage: dump_rows.py <이미지> [<이미지> ...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def dump(path):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    h, w = a.shape
    print(f"=== {Path(path).parent.name}/{Path(path).name}  {w}x{h}")
    print(f"{'y':>5} {'frac':>6} {'white':>6} {'dark':>6} {'mid':>6} {'mean':>6} {'std':>6} {'edges':>6}")
    STEP = max(1, h // 128)
    for y in range(0, h, STEP):
        row = a[y]
        white = (row >= 200).mean()
        dark  = (row <= 100).mean()
        mid   = 1.0 - white - dark
        # 가로 방향 밝기 전환 횟수 = 건반 줄무늬 지표
        b = (row >= 150).astype(np.int8)
        edges = int(np.abs(np.diff(b)).sum())
        print(f"{y:>5} {y/h:>6.3f} {white:>6.2f} {dark:>6.2f} {mid:>6.2f} "
              f"{row.mean():>6.1f} {row.std():>6.1f} {edges:>6d}")
    print()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        dump(p)
