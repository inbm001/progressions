# 샘플 1개만 받아서 프레임을 뽑는다. 화면 레이아웃 확인용.
$ErrorActionPreference = "Stop"

$root   = "D:\claude\chord-progression-collecting"
$work   = Join-Path $root "work"
$frames = Join-Path $work "frames"
$ffmpeg = "C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
$vid    = "Vloi0u62MQM"

New-Item -ItemType Directory -Force -Path $work, $frames | Out-Null

uvx yt-dlp -f "bv*+ba/b" -S "res:720" --no-warnings --ffmpeg-location $ffmpeg `
    -o "$work\%(id)s.%(ext)s" "https://www.youtube.com/watch?v=$vid"

$video = Get-ChildItem $work -Filter "$vid.*" | Where-Object { $_.Extension -in ".mp4",".webm",".mkv" } | Select-Object -First 1
& $ffmpeg -y -i $video.FullName -vf "fps=1" -q:v 3 "$frames\${vid}_%03d.jpg"

Write-Output "---- frames ----"
(Get-ChildItem $frames -Filter "$vid*").Count
