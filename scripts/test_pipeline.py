"""자동 크롭이 들어간 파이프라인을 지정 영상들로 시험한다.

usage: test_pipeline.py <videoId> [...]
      done/ 을 건드리지 않고 done_test/ 에 결과를 쓴다.
"""
import sys, json, time, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect

ROOT = Path(r"D:\claude\chord-progression-collecting")

# 본 실행과 섞이지 않도록 출력 위치를 갈아끼운다
collect.DONE = ROOT / "done_test"
collect.WORK = ROOT / "work_test"
collect.DONE.mkdir(exist_ok=True)
collect.WORK.mkdir(exist_ok=True)


def main(vids):
    entries = [{"id": v, "title": v} for v in vids]
    for e in entries:
        t = time.perf_counter()
        collect.fetch(e)
        t_dl = time.perf_counter() - t

        t = time.perf_counter()
        rec = collect.process(e)
        t_oc = time.perf_counter() - t

        band = rec.get("band", {})
        print(f"=== {e['id']}  dl={t_dl:.0f}s ocr={t_oc:.0f}s")
        print(f"  band: {band}")
        print(f"  status={rec['status']}  ocr_rate={rec.get('ocr_rate')}  "
              f"frames={rec.get('n_frames')} ocr={rec.get('n_ocr')}")
        prog = rec.get("progression", [])
        print(f"  chords={len(prog)}")
        for p in prog[:12]:
            print(f"    {p['at']:>6.2f}s {p['dur']:>5.2f}s  {p['chord']}")
        if len(prog) > 12:
            print(f"    ... +{len(prog)-12}")
        if rec.get("unparsed"):
            print(f"  unparsed: {rec['unparsed'][:8]}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
