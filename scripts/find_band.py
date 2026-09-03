"""코드 심볼 띠의 세로 위치를 자동으로 찾는다.

실측에서 나온 판별식
  건반은 세로 줄무늬라, 여러 행에 걸쳐 가로 방향 밝기 전환 횟수(edges)가
  거의 변하지 않는다. 글자 띠는 행마다 edges 가 크게 널뛴다.
  (실측: 건반 61,61,61,61,61 / 글자 띠 0,20,32,50,42,40,6,0)

  따라서
    keyboard = edges 가 충분히 크고(>=24), 세로로 안정적인(std 작은) 구간
    band     = 밝은 배경이 지배적이고, 건반이 아닌 구간
  중 건반 바로 위를 코드 띠로 잡는다.

usage: find_band.py <이미지 경로> [...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

WHITE_TH = 200      # 이 이상이면 밝은 픽셀
DARK_TH  = 100      # 이 이하면 어두운 픽셀
BIN_TH   = 150      # edges 계산용 이진화 기준
EDGE_MIN = 24       # 건반으로 볼 최소 줄무늬 수
EDGE_WIN = 9        # 안정성을 볼 세로 창 크기(행)
EDGE_STD = 6.0      # 이 창 안에서 edges 표준편차가 이보다 작으면 '안정'
KEY_DARK = 0.18     # 건반은 검은 키 때문에 어두운 픽셀이 이만큼은 된다.
                    # 글자도 edges 를 만들지만 dark 는 0.1 을 넘지 않는다.


def profiles(path):
    a = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    h, w = a.shape
    white = (a >= WHITE_TH).mean(axis=1)
    dark  = (a <= DARK_TH).mean(axis=1)
    b = (a >= BIN_TH).astype(np.int8)
    edges = np.abs(np.diff(b, axis=1)).sum(axis=1)
    return (h, w), white, dark, edges


def _rolling_std(x, win):
    """각 행 주변 win 행의 표준편차."""
    n = len(x)
    out = np.full(n, 1e9)
    half = win // 2
    for i in range(n):
        a, b = max(0, i - half), min(n, i + half + 1)
        out[i] = x[a:b].std()
    return out


def _runs(mask, min_h):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(mask) - 1))
    return [r for r in out if (r[1] - r[0] + 1) >= min_h]


def find_band(path, debug=False):
    """(top_frac, height_frac) 을 돌려준다. 못 찾으면 None."""
    (h, w), white, dark, edges = profiles(path)
    estd = _rolling_std(edges.astype(float), EDGE_WIN)

    # 1) 건반: 줄무늬가 많고, 세로로 안정적이고, 검은 키가 있어 어둡다.
    #    dark 조건이 없으면 큰 글자가 만드는 줄무늬를 건반으로 오인한다.
    kb_mask = (edges >= EDGE_MIN) & (estd <= EDGE_STD) & (dark >= KEY_DARK)
    keys = _runs(kb_mask, int(h * 0.03))

    # 2) 심볼 띠는 '밝은 배경' 이지만, 글자 획이 지나는 행은 white 가 떨어진다.
    #    따라서 좁은 임계로 자르지 않고, 건반 위에서 위로 거슬러 올라가며
    #    '배경이 여전히 밝은' 동안 확장한다.
    if debug:
        print(f"  size={w}x{h}")
        for a, b in keys:
            print(f"  KEYS {a:4d}-{b:4d}  ({a/h:.3f}-{b/h:.3f})  "
                  f"edges~{edges[a:b+1].mean():.0f}")

    if not keys:
        return None

    # 건반 후보가 여럿이다(앨범 재킷·연주 손 등도 줄무늬로 잡힌다).
    # '가장 위'를 쓰면 사진 노이즈에 걸리므로, 후보마다 실제로 그 위에
    # 글자 띠가 붙어 있는지 확인하고 띠 품질로 고른다.
    best = None
    for ka, kb in keys:
        # 안정 구간 판정은 창(window) 때문에 건반 상단을 몇 행 놓친다.
        # 확장에는 dark 조건을 걸지 않는다. 건반 상단은 검은 키 사이
        # 흰 부분이라 dark 가 낮아, 조건을 걸면 경계를 못 찾는다.
        top_key = ka
        while top_key > 0 and edges[top_key - 1] >= EDGE_MIN:
            top_key -= 1

        # 건반 바로 위부터 위로 확장.
        # 글자 획이 지나는 행도 배경은 밝으므로 '밝은 픽셀 절반 이상'.
        # 건반과 띠 사이에는 경계선·그림자가 한두 행 끼므로,
        # 어두운 행을 만나도 SKIP 행까지는 건너뛰며 살펴본다.
        SKIP = max(2, int(h * 0.004))
        y = top_key - 1
        miss = 0
        last_good = top_key
        while y >= 0:
            if white[y] >= 0.50:
                last_good = y
                miss = 0
            else:
                miss += 1
                if miss > SKIP:
                    break
            y -= 1
        bt, bb = last_good, top_key - 1

        # 확장이 순백 여백에서 끝났다면 글자를 아직 못 만난 것이다.
        # (코드 심볼이 건반과 같은 흰 판 위에 있어, 건반 사이에 여백이
        #  한 줄 낀 배치) 위쪽에 밝은 영역이 이어지면 계속 올라간다.
        if bb >= bt and dark[bt:bb + 1].max() < 0.02:
            y2 = bt - 1
            while y2 >= 0 and white[y2] >= 0.50:
                y2 -= 1
            if bt - (y2 + 1) >= h * 0.01:
                bt = y2 + 1

        bh_px = bb - bt + 1
        if bh_px < h * 0.02 or bh_px > h * 0.15:
            if debug:
                print(f"  drop size {bt:4d}-{bb:4d} h={bh_px/h:.3f} "
                      f"(keys {ka}-{kb}, top_key={top_key})")
            continue

        seg_white = white[bt:bb + 1]
        seg_dark  = dark[bt:bb + 1]

        # 코드 심볼 띠는 '순백 단색 배경 + 검은 글자' 다.
        #   - 글자가 없는 여백 행이 반드시 있다 (white ~1.0)
        #   - 글자가 있는 행도 있다 (dark 가 어느 정도)
        # 사진이나 나무 피아노는 순백 행이 없어 여기서 걸러진다.
        purity = seg_white.max()          # 가장 깨끗한 행
        has_ink = seg_dark.max()          # 글자 흔적
        if purity < 0.95 or has_ink < 0.02:
            if debug:
                print(f"  drop band {bt:4d}-{bb:4d} "
                      f"purity={purity:.3f} ink={has_ink:.3f}")
            continue

        # 여러 개가 남으면 더 깨끗한(= 배경이 흰) 쪽을 고른다.
        score = seg_white.mean()
        if debug:
            print(f"  cand band {bt:4d}-{bb:4d} ({bt/h:.3f}-{bb/h:.3f}) "
                  f"over keys {ka}-{kb}  purity={purity:.3f} "
                  f"ink={has_ink:.3f} score={score:.3f}")
        if best is None or score > best[0]:
            best = (score, bt, bb)

    if best is None:
        if debug:
            print("  no valid band")
        return None

    _, band_top, band_bot = best
    if debug:
        print(f"  BAND {band_top:4d}-{band_bot:4d}  "
              f"({band_top/h:.3f}-{band_bot/h:.3f})  "
              f"h={(band_bot-band_top+1)/h:.3f}")

    return band_top / h, (band_bot - band_top + 1) / h


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(Path(p).parent.name, "/", Path(p).name)
        r = find_band(p, debug=True)
        if r:
            print(f"  -> top={r[0]:.4f} h={r[1]:.4f}")
        else:
            print("  -> None")
        print()
