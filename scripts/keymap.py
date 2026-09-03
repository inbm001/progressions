"""건반 키 좌표 → MIDI 노트 매핑을 만들고 눌린 음을 읽는다."""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image

KEY_TOP    = 790     # 건반 상단
BLACK_ROW  = 830     # 검은건반만 존재하는 높이
WHITE_ROW  = 905     # 검은건반 아래, 흰건반만 존재하는 높이
NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]


def is_orange(px):
    r, g, b = px
    return r > 150 and 90 < g < 210 and b < 110 and r - b > 80


def build_keymap(img):
    """검은건반 x중심 목록에서 옥타브 패턴을 찾아 전체 키맵을 만든다."""
    W = img.shape[1]
    row = img[BLACK_ROW]
    # 검은건반 = 어둡거나(미압) 주황(압)인 연속 런
    key = np.array([
        (row[x] < 80).all() or is_orange(row[x]) for x in range(W)
    ])
    runs, s = [], None
    for x in range(W):
        if key[x] and s is None: s = x
        elif not key[x] and s is not None:
            if x - s >= 8: runs.append(((s + x - 1) // 2, s, x - 1))
            s = None
    if s is not None and W - s >= 8: runs.append(((s + W - 1) // 2, s, W - 1))
    return runs


def read_pressed(img, blacks, white_edges, base_midi):
    """눌린 검은건반/흰건반을 MIDI 노트로 반환."""
    notes = []
    # 검은건반
    for i, (cx, x0, x1) in enumerate(blacks):
        if is_orange(img[BLACK_ROW, cx]):
            notes.append(("b", i, cx))
    # 흰건반
    for i in range(len(white_edges) - 1):
        cx = (white_edges[i] + white_edges[i + 1]) // 2
        if is_orange(img[WHITE_ROW, cx]):
            notes.append(("w", i, cx))
    return notes


if __name__ == "__main__":
    f = Path(sys.argv[1])
    img = np.asarray(Image.open(f).convert("RGB")).astype(int)
    blacks = build_keymap(img)
    print(f"black keys found: {len(blacks)}")
    print("centers:", [c for c, _, _ in blacks])
    # 검은건반 간격으로 2-3 그룹 패턴 확인
    cs = [c for c, _, _ in blacks]
    gaps = [cs[i+1] - cs[i] for i in range(len(cs)-1)]
    print("gaps:", gaps)
