"""배치가 다른 영상의 화면 구조를 확인한다.

usage: probe_layout.py <videoId> [<videoId> ...]

각 영상에서 프레임 몇 장을 전체 높이로 뽑아 probe/<vid>/ 에 저장한다.
크롭을 하지 않으므로 화면 어디에 코드 띠가 있는지 눈으로 볼 수 있다.
"""
import sys, subprocess
from pathlib import Path

ROOT   = Path(r"D:\claude\chord-progression-collecting")
PROBE  = ROOT / "probe"
FFMPEG = r"C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
YTDLP  = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]


def probe(vid):
    d = PROBE / vid
    d.mkdir(parents=True, exist_ok=True)
    vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        print(f"[dl] {vid}", flush=True)
        subprocess.run(
            YTDLP + ["-f", "bv*/b", "-S", "res:720", "--no-warnings", "-q",
                     "--ffmpeg-location", FFMPEG,
                     "-o", str(d / "v.%(ext)s"),
                     f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True)
        vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        print(f"[fail] {vid} download", flush=True)
        return

    # 전체 화면을 1초당 1장, 앞 12초만
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
         "-t", "12", "-vf", "fps=1", "-q:v", "2", str(d / "full_%02d.jpg")],
        capture_output=True)
    print(f"[ok] {vid} -> {len(list(d.glob('full_*.jpg')))} frames", flush=True)


if __name__ == "__main__":
    for v in sys.argv[1:]:
        probe(v)
