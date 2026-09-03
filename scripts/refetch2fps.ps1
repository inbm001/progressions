param([string]$vid = "Ggnq80BOWOQ")
$ErrorActionPreference = "Stop"
$ffmpeg = "C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
$d = "D:\claude\chord-progression-collecting\run2\$vid"
New-Item -ItemType Directory -Force -Path $d | Out-Null

uvx yt-dlp -f "bv*/b" -S "res:720" --no-warnings -q --ffmpeg-location $ffmpeg -o "$d\v.%(ext)s" "https://www.youtube.com/watch?v=$vid"
$vf = Get-ChildItem $d -Filter "v.*" | Select-Object -First 1
& $ffmpeg -y -loglevel error -i $vf.FullName -vf "fps=4,crop=iw:ih*0.055:0:ih*0.5625,scale=720:-1" -q:v 3 "$d\f_%04d.jpg"
(Get-ChildItem $d -Filter "f_*.jpg").Count
