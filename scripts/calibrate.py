"""건반 캘리브레이션 v3 — 밴드 내부로 한정하고 키 지오메트리를 확정한다."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

BAND_TOP, BAND_BOT = 722, 937           # v2에서 검출된 흰 밴드
KEY_TOP = 785                            # 코드 심볼 아래, 건반 시작 (추정)

f = Path(sys.argv[1])
img = np.asarray(Image.open(f).convert("RGB")).astype(int)
H, W, _ = img.shape

band = img[BAND_TOP:BAND_BOT]
# 건반 실제 시작: 행별 검은픽셀 비율이 급증하는 지점
blk = (band < 70).all(axis=2).mean(axis=1)
for i, v in enumerate(blk):
    if v > 0.15:
        print(f"keys start at y={BAND_TOP+i} (black ratio {v:.2f})")
        ks = BAND_TOP + i
        break

print("\n--- black ratio per row in band ---")
for i in range(0, len(blk), 8):
    print(f"y={BAND_TOP+i}: {blk[i]:.3f}")
