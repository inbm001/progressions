"""금요일 밤 상황을 1곡으로 재현한다.

대화창 안에서 실행한 작업이, 대화창이 끊길 때 함께 끝나는지 확인한다.

usage: repro_kill.py <videoId>
      done_repro/ 에 결과를 쓴다. 본 수집에는 손대지 않는다.
"""
import sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect

ROOT = Path(r"D:\claude\chord-progression-collecting")
collect.DONE = ROOT / "done_repro"
collect.WORK = ROOT / "work_repro"
collect.DONE.mkdir(exist_ok=True)
collect.WORK.mkdir(exist_ok=True)
collect.PUBLISH = False          # 재현이므로 깃허브에 올리지 않는다

import os


def main(vid):
    print(f"[pid] 이 프로세스 = {os.getpid()}", flush=True)
    print(f"[pid] 부모 = {os.getppid()}", flush=True)

    e = {"id": vid, "title": vid}

    t = time.perf_counter()
    collect.fetch(e)
    print(f"[dl] {time.perf_counter()-t:.0f}초", flush=True)

    t = time.perf_counter()
    rec = collect.process(e)
    print(f"[ocr] {time.perf_counter()-t:.0f}초", flush=True)

    print(f"[결과] {rec['status']} 판독률={rec.get('ocr_rate')} "
          f"코드={len(rec.get('progression', []))}개", flush=True)

    # 프레임과 영상은 process 안에서 지워진다. 남은 폴더만 정리한다.
    import shutil
    shutil.rmtree(collect.WORK, ignore_errors=True)
    print("[정리] 작업 폴더 삭제. CPU 사용 끝", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
