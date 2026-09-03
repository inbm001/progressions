"""yt-dlp 제목 출력의 실제 인코딩을 확인한다."""
import subprocess

YTDLP = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]
URL = "https://www.youtube.com/watch?v=-gDI19p8oq0"

import os
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
r = subprocess.run(
    YTDLP + ["--flat-playlist", "--print", "%(title)s", URL],
    capture_output=True, env=env)          # bytes 그대로

raw = r.stdout.strip()
print("raw bytes:", raw[:120])
for enc in ("utf-8", "cp949", "cp1252"):
    try:
        print(f"{enc:>8}: {raw.decode(enc)[:80]}")
    except Exception as e:
        print(f"{enc:>8}: FAIL {e}")
