"""재생목록 앞부분 N개를 병렬 다운로드+프레임추출해 실제 처리량을 잰다."""
import sys, time, json, subprocess, concurrent.futures as cf
from pathlib import Path

ROOT   = Path(r"D:\claude\chord-progression-collecting")
WORK   = ROOT / "bench"
FFMPEG = r"C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
YTDLP  = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]

N       = int(sys.argv[1]) if len(sys.argv) > 1 else 8
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
PLAYLIST = "https://www.youtube.com/playlist?list=UUSHzk0LV3F-MIFS-fGweXhNmQ"

WORK.mkdir(exist_ok=True)

# 1) 목록
t0 = time.perf_counter()
r = subprocess.run(
    YTDLP + ["--flat-playlist", "-J", "--playlist-end", str(N), PLAYLIST],
    capture_output=True, text=True, encoding="utf-8", errors="replace")
t_list = time.perf_counter() - t0
data = json.loads(r.stdout)
entries = [(e["id"], e.get("title", "")) for e in data["entries"]]
print(f"[list] {len(entries)} ids in {t_list:.1f}s")


def one(item):
    vid, title = item
    t = time.perf_counter()
    d = WORK / vid
    d.mkdir(exist_ok=True)
    # 영상만 (오디오 불필요) — 가장 낮은 해상도 중 480p 이상
    subprocess.run(
        YTDLP + ["-f", "bv*/b", "-S", "res:720", "--no-warnings", "-q",
                 "--ffmpeg-location", FFMPEG,
                 "-o", str(d / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True)
    t_dl = time.perf_counter() - t
    vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        return vid, t_dl, None, 0
    t = time.perf_counter()
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
         "-vf", "fps=1,crop=iw:ih*0.055:0:ih*0.5625,scale=720:-1",
         "-q:v", "3", str(d / "f_%03d.jpg")],
        capture_output=True)
    t_fr = time.perf_counter() - t
    n = len(list(d.glob("f_*.jpg")))
    return vid, t_dl, t_fr, n


t0 = time.perf_counter()
results = []
with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for res in ex.map(one, entries):
        results.append(res)
        print(f"  {res[0]}: dl={res[1]:.1f}s frames={res[3]}")
wall = time.perf_counter() - t0

ok = [r for r in results if r[2] is not None]
print(f"\n[bench] {len(entries)} videos, {WORKERS} workers")
print(f"  wall: {wall:.1f}s  =>  {wall/len(entries):.2f}s per video")
print(f"  ok: {len(ok)}/{len(entries)}")
print(f"  total frames: {sum(r[3] for r in ok)}")
print(f"  projected 1478 videos: {wall/len(entries)*1478/60:.1f} min")
