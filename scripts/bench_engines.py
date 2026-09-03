"""OCR 엔진/설정별 속도와 정확도를 한 번에 잰다.

기준(baseline) = rapidocr 기본 설정. 이 결과와 문자열이 같아야 '정확'으로 본다.
12시간 = 43200초 / 1478곡 = 곡당 29초가 목표선.
"""
import os, time, json
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
SRC = Path(r"D:\claude\chord-progression-collecting\run2\Ggnq80BOWOQ")
frames = sorted(SRC.glob("f_*.jpg"))[:80]
print(f"frames: {len(frames)}\n")

from rapidocr_onnxruntime import RapidOCR

results = {}

# --- A. baseline ---
eng = RapidOCR()
t0 = time.perf_counter()
base = []
for f in frames:
    r, _ = eng(str(f))
    base.append(" ".join(x[1] for x in r) if r else "")
tA = time.perf_counter() - t0
results["A_baseline"] = (tA, len(frames))
print(f"A baseline            {tA:6.1f}s  {tA/len(frames)*1000:5.0f}ms/f")

# --- B. 검출 파라미터 완화: 작은 이미지이므로 det 입력 축소 ---
for limit in (320, 480, 640):
    eng2 = RapidOCR(det_limit_side_len=limit)
    t0 = time.perf_counter()
    out = []
    for f in frames:
        r, _ = eng2(str(f))
        out.append(" ".join(x[1] for x in r) if r else "")
    t = time.perf_counter() - t0
    same = sum(1 for a, b in zip(base, out) if a.replace(" ", "") == b.replace(" ", ""))
    print(f"B det_limit={limit:<4}      {t:6.1f}s  {t/len(frames)*1000:5.0f}ms/f  match {same}/{len(frames)}")

# --- C. cls 끄기 ---
t0 = time.perf_counter()
out = []
for f in frames:
    r, _ = eng(str(f), use_cls=False)
    out.append(" ".join(x[1] for x in r) if r else "")
tC = time.perf_counter() - t0
same = sum(1 for a, b in zip(base, out) if a.replace(" ", "") == b.replace(" ", ""))
print(f"C no-cls              {tC:6.1f}s  {tC/len(frames)*1000:5.0f}ms/f  match {same}/{len(frames)}")

print(f"\n목표: 곡당 29초. 현재 곡당 프레임 ~90장 OCR -> 프레임당 322ms 이하 필요")
