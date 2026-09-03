"""중복 프레임 제거 효과와 병렬 OCR 실처리량을 잰다.

코드 심볼 크롭은 코드가 바뀔 때만 달라진다. 연속 프레임 해시가 같으면 버린다.
"""
import time, os
from pathlib import Path
import concurrent.futures as cf
import numpy as np
from PIL import Image

BENCH = Path(r"D:\claude\chord-progression-collecting\bench")

# rapidocr는 프로세스당 스레드를 다 잡아 6프로세스가 서로 경합한다. 1로 묶는다.
os.environ["OMP_NUM_THREADS"] = "1"


def dhash(path, size=16):
    im = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(im, dtype=int)
    return (a[:, 1:] > a[:, :-1]).tobytes()


def measure_dedup():
    t0 = time.perf_counter()
    total, keep = 0, []
    for d in sorted(x for x in BENCH.iterdir() if x.is_dir()):
        prev = None
        for f in sorted(d.glob("f_*.jpg")):
            total += 1
            h = dhash(f)
            if h != prev:
                keep.append(f)
            prev = h
    el = time.perf_counter() - t0
    print(f"[dedup] {total} -> {len(keep)} frames ({len(keep)/total*100:.1f}% kept) in {el:.1f}s")
    print(f"  dedup cost: {el/total*1000:.1f}ms/frame")
    return keep


keep_list = measure_dedup() if __name__ == "__main__" else []


# --- 2) 병렬 OCR 실측 ---
def run(paths):
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    n = 0
    for p in paths:
        ocr(str(p))
        n += 1
    return n


if __name__ == "__main__":
    for W in (1, 6, 12):
        chunks = [keep_list[i::W] for i in range(W)]
        t0 = time.perf_counter()
        with cf.ProcessPoolExecutor(max_workers=W) as ex:
            list(ex.map(run, chunks))
        el = time.perf_counter() - t0
        per = el / len(keep_list)
        print(f"[ocr x{W}] {len(keep_list)} frames in {el:.1f}s ({per*1000:.0f}ms/frame)")
        print(f"  throughput: {1/per:.1f} frames/s")
