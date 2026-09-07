# 수집이 돌고 있는지 보고, 없으면 띄운다.
# 작업 스케줄러가 한 시간마다 부른다.
# 이미 돌고 있으면 아무것도 하지 않는다.

$ErrorActionPreference = "SilentlyContinue"

$Root = "D:\claude\chord-progression-collecting"
$Log  = "$Root\out\keepalive.log"
$Uv   = "C:\Users\inbm\.local\bin\uv.exe"

function Note([string]$m) {
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $Log -Value "$t  $m" -Encoding utf8
}

$running = @(Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
             Where-Object { $_.CommandLine -like "*collect.py*" })

if ($running.Count -gt 0) {
    Note "running"
    exit 0
}

$idx = "$Root\data\index.json"
if (Test-Path -LiteralPath $idx) {
    try {
        $d = Get-Content -LiteralPath $idx -Raw -Encoding utf8 | ConvertFrom-Json
        if ($d.count -ge 1479) {
            Note "done $($d.count)"
            exit 0
        }
    } catch { }
}

Note "starting"

Start-Process -FilePath $Uv `
    -ArgumentList @(
        "run", "--with", "pillow", "--with", "numpy",
        "--with", "rapidocr-onnxruntime", "python",
        "$Root\scripts\collect.py", "all", "4", "3"
    ) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput "$Root\out\run.log" `
    -RedirectStandardError "$Root\out\run.err.log" `
    -WindowStyle Hidden

Note "started"
