"""건반 후보별 '주황 강조 픽셀' 비율을 잰다.

코드 심볼 띠 바로 아래 건반은 눌린 음이 주황으로 칠해져 있다.
연주 영상의 실제 피아노에는 이 색이 없다. 이 성질로 두 건반을 가른다.

usage: dump_color.py <이미지> [...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import find_band as fb


def orange_frac(rgb):
    """행별 주황 픽셀 비율. 주황 = R 높고 G 중간 B 낮음."""
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    m = (r > 120) & (r - b > 50) & (r - g > 20) & (g - b > 10)
    return m.mean(axis=1)


def main(path):
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im)
    h, w = rgb.shape[:2]
    (hh, ww), white, dark, edges = fb.profiles(path)
    estd = fb._rolling_std(edges.astype(float), fb.EDGE_WIN)
    keys = fb._runs((edges >= fb.EDGE_MIN) & (estd <= fb.EDGE_STD),
                    int(h * 0.03))
    orf = orange_frac(rgb)

    print(f"=== {Path(path).parent.name}  {w}x{h}")
    for a, b in keys:
        print(f"  KEYS {a:4d}-{b:4d} ({a/h:.3f}-{b/h:.3f}) "
              f"edges~{edges[a:b+1].mean():5.1f} "
              f"orange={orf[a:b+1].mean():.4f} max={orf[a:b+1].max():.4f}")
    print()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
