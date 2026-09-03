"""재생목록에서 무작위 표본을 뽑아 자동 크롭 파이프라인을 검증한다.

usage: sample_check.py <표본수> [<seed>]
      done_test/ 에 결과를 쓰고 요약을 출력한다.
"""
import sys, json, random, time
from pathlib import Path

# 콘솔 기본 인코딩(cp949)이 이모지 제목을 못 찍어 죽는 것을 막는다
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
import collect

ROOT = Path(r"D:\claude\chord-progression-collecting")
collect.DONE = ROOT / "done_test"
collect.WORK = ROOT / "work_test"
collect.DONE.mkdir(exist_ok=True)
collect.WORK.mkdir(exist_ok=True)


def playlist():
    cache = ROOT / "out" / "playlist_full.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import subprocess
    r = subprocess.run(
        collect.YTDLP + ["--flat-playlist", "-J", collect.PLAYLIST],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    entries = [{"id": e["id"], "title": e.get("title", "")}
               for e in json.loads(r.stdout)["entries"]]
    cache.write_text(json.dumps(entries, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return entries


def main(n, seed):
    entries = playlist()
    print(f"[list] {len(entries)} videos", flush=True)
    random.Random(seed).shuffle(entries)
    pick = entries[:n]

    T0 = time.perf_counter()
    recs = []
    for i, e in enumerate(pick, 1):
        p = collect.DONE / f"{e['id']}.json"
        if p.exists():
            recs.append(json.loads(p.read_text(encoding="utf-8")))
            continue
        collect.fetch(e)
        rec = collect.process(e)
        recs.append(rec)
        b = rec.get("band", {})
        print(f"[{i}/{n}] {rec['id']} {rec['status']:>16} "
              f"rate={rec.get('ocr_rate', 0):.2f} "
              f"chords={len(rec.get('progression', [])):>3} "
              f"top={b.get('top', 0):.3f} h={b.get('h', 0):.3f} "
              f"{b.get('how', '')}", flush=True)

    ok  = [r for r in recs if r["status"] == "ok"]
    bad = [r for r in recs if r["status"] != "ok"]
    auto = [r for r in recs if r.get("band", {}).get("how", "").startswith("auto")]

    print()
    print(f"=== 표본 {len(recs)}곡  ({(time.perf_counter()-T0)/60:.1f}분)")
    print(f"  ok       {len(ok)}  ({len(ok)/len(recs):.0%})")
    print(f"  failed   {len(bad)}")
    print(f"  자동탐지 {len(auto)}/{len(recs)}")
    tops = sorted(r["band"]["top"] for r in auto)
    if tops:
        print(f"  top 분포 min={tops[0]:.3f} med={tops[len(tops)//2]:.3f} "
              f"max={tops[-1]:.3f}")
        # 기본값에서 크게 벗어난 곡 = 배치가 다른 영상
        odd = [r for r in auto if abs(r["band"]["top"] - 0.5625) > 0.02]
        print(f"  배치 다름 {len(odd)}곡")
        for r in odd:
            print(f"    {r['id']} top={r['band']['top']:.3f} "
                  f"{r['status']} rate={r.get('ocr_rate', 0):.2f}")
    if bad:
        print("  실패 목록:")
        for r in bad:
            print(f"    {r['id']} {r['status']} rate={r.get('ocr_rate', 0):.2f} "
                  f"{r['title'][:50]}")
            for u in r.get("unparsed", [])[:4]:
                print(f"       {u!r}")

    allbad = []
    for r in recs:
        allbad += r.get("unparsed", [])
    print(f"  파싱 실패 문자열 {len(allbad)}건")
    for u in allbad[:20]:
        print(f"    {u!r}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    main(n, seed)
