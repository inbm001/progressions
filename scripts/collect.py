"""코드진행 + 지속시간 + 제목/아티스트 전량 수집.

usage: collect.py [N] [dl_workers] [ocr_workers]
  N 생략 = 재생목록 전체

특징
  - 곡 단위 재개: 이미 done/<vid>.json 이 있으면 건너뛴다. 중단해도 이어짐.
  - 곡 처리가 끝나면 프레임을 즉시 삭제한다 (디스크 절약).
  - 판독 실패곡은 failed.json 으로 따로 분류한다.
"""
import os, re, sys, json, time, shutil, subprocess
import concurrent.futures as cf
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from find_band import find_band

# 콘솔 기본 인코딩(cp949)이 이모지 제목을 못 찍어 죽는 것을 막는다
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ["OMP_NUM_THREADS"] = "1"

# 코드 심볼 띠 기본 위치(대다수 영상). 자동 탐지가 실패하면 이 값을 쓴다.
BAND_TOP_DEFAULT = 0.5625
BAND_H_DEFAULT   = 0.055

FPS    = 4
ROOT   = Path(r"D:\claude\chord-progression-collecting")
WORK   = ROOT / "work_frames"
DONE   = ROOT / "done"
OUT    = ROOT / "out"
FFMPEG = r"C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
YTDLP  = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]
PLAYLIST = "https://www.youtube.com/playlist?list=UUSHzk0LV3F-MIFS-fGweXhNmQ"

# ---------- 코드 심볼 문법 ----------
RT   = r"[A-G][#b♭♯]?"
TAIL = r"[A-Za-z0-9#b()/♭♯+\-°øΔ, .]*"
PAT  = re.compile(rf"^{RT}\s*{TAIL}$")
SWAP = re.compile(rf"^(.+?)\s+({RT})$")
NC   = re.compile(rf"^({RT})\s*n\.?c\.?$", re.I)      # "Bb n.c." = 코드 없음 표기

FIXES = [
    (r"\|", ""),
    (r"\bMajl", "Maj1"), (r"\bminl", "min1"),
    (rf"^({RT})\s+1\s+(?=\d)", r"\1 "),
    (r"\s+", " "),
]


def normalize(s: str):
    for a, b in FIXES:
        s = re.sub(a, b, s)
    s = s.strip()
    if not s:
        return None
    if NC.match(s):
        return NC.match(s).group(1) + " N.C."
    if PAT.match(s):
        return s
    m = SWAP.match(s)
    if m:
        c = f"{m.group(2)} {m.group(1)}"
        if PAT.match(c):
            return c
    return None


# ---------- rec-only OCR 의 꼬리 잡음 제거 ----------
# 검출 단계를 끄면 30배 빠르지만 여백을 e/u/n/m/o 로 오독한다.
# 'sus'/'min'/'dim' 등 실제 코드 문자를 깎지 않도록, 잡음 문자만 뒤에서 벗긴다.
FULLWIDTH = str.maketrans("（）＃", "()#")
TAILJUNK  = re.compile(r"(?<=[0-9)\]])[eunmo\-\s]+$")   # 숫자/닫는괄호 뒤 잡음만
TAILJUNK2 = re.compile(r"[eunmo\-\s]{2,}$")             # 2자 이상 연속 잡음


def clean_rec(s: str) -> str:
    s = s.translate(FULLWIDTH)
    s = TAILJUNK.sub("", s)
    s = TAILJUNK2.sub("", s)
    if s.count("(") > s.count(")"):
        s += ")"
    m = re.match(rf"^({RT})\s*(.*)$", s)
    if m:
        s = f"{m.group(1)} {m.group(2)}".strip()
    return re.sub(r"\s+", " ", s).strip()


def dhash(p, size=16):
    a = np.asarray(Image.open(p).convert("L").resize((size + 1, size), Image.LANCZOS), int)
    return (a[:, 1:] > a[:, :-1]).tobytes()


# ---------- 1. 다운로드 + 프레임 ----------
def detect_band(vf, d):
    """영상에서 표본 프레임을 뽑아 코드 심볼 띠 위치를 찾는다.

    영상마다 화면 배치가 달라 크롭을 고정하면 건반을 글자로 오독한다.
    표본 여러 장에서 탐지한 뒤 중앙값을 써서 한 장의 실패에 흔들리지 않게 한다.
    돌려주는 값은 (top, height) 비율. 실패하면 기본값.
    """
    s = d / "_probe"
    s.mkdir(exist_ok=True)
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
         "-vf", "fps=1/3", "-frames:v", "5", "-q:v", "2",
         str(s / "p_%02d.jpg")],
        capture_output=True)

    hits = [r for r in (find_band(p) for p in sorted(s.glob("p_*.jpg"))) if r]
    shutil.rmtree(s, ignore_errors=True)

    if not hits:
        return BAND_TOP_DEFAULT, BAND_H_DEFAULT, "default"

    tops = sorted(x[0] for x in hits)
    hs   = sorted(x[1] for x in hits)
    top  = tops[len(tops) // 2]
    bh   = hs[len(hs) // 2]

    # 터무니없는 값은 버린다 (띠는 화면 중하단, 높이 2~12%)
    if not (0.30 <= top <= 0.80 and 0.02 <= bh <= 0.12):
        return BAND_TOP_DEFAULT, BAND_H_DEFAULT, "default"

    # 여유는 위쪽에만 준다. 띠 아래는 건반이 바로 붙어 있어,
    # 아래로 넓히면 검은 키 조각이 들어와 글자로 오독된다.
    # 아래쪽은 오히려 살짝 깎아 건반이 섞이지 않게 한다.
    pad_top = bh * 0.10
    cut_bot = bh * 0.04
    new_top = max(0.0, top - pad_top)
    new_bh  = (top + bh - cut_bot) - new_top
    return new_top, new_bh, f"auto({len(hits)}/5)"


def fetch(e):
    vid = e["id"]
    d = WORK / vid
    d.mkdir(parents=True, exist_ok=True)
    if list(d.glob("f_*.jpg")):
        return vid
    subprocess.run(
        YTDLP + ["-f", "bv*/b", "-S", "res:720", "--no-warnings", "-q",
                 "--ffmpeg-location", FFMPEG,
                 "-o", str(d / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True)
    vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        return vid

    top, bh, how = detect_band(vf, d)
    (d / "band.json").write_text(
        json.dumps({"top": top, "h": bh, "how": how}), encoding="utf-8")

    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
         "-vf", f"fps={FPS},crop=iw:ih*{bh:.6f}:0:ih*{top:.6f},scale=720:-1",
         "-q:v", "3", str(d / "f_%04d.jpg")],
        capture_output=True)
    vf.unlink(missing_ok=True)
    return vid


# ---------- 2. 한 곡 OCR -> 구간 ----------
def process(entry):
    """워커 프로세스. 한 곡을 통째로 처리하고 done/<vid>.json 을 쓴다."""
    from rapidocr_onnxruntime import RapidOCR
    global _ENGINE
    try:
        eng = _ENGINE
    except NameError:
        eng = _ENGINE = RapidOCR()

    vid, title = entry["id"], entry["title"]
    d = WORK / vid
    bandinfo = {}
    bp = d / "band.json"
    if bp.exists():
        try:
            bandinfo = json.loads(bp.read_text(encoding="utf-8"))
        except Exception:
            pass
    frames = sorted(d.glob("f_*.jpg"))
    if not frames:
        rec = {"id": vid, "title": title, "url": f"https://www.youtube.com/watch?v={vid}",
               "status": "no_frames", "progression": []}
        (DONE / f"{vid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        return rec

    # dedup
    todo, prev = [], None
    for f in frames:
        h = dhash(f)
        if h != prev:
            todo.append(f)
        prev = h

    # ocr — 검출 생략(rec-only)은 30배 빠르나 여백을 글자로 오독해 정확도가 무너진다.
    # 세 방식(축소·rec-only·rec으로 변화감지)을 재봤고 모두 실패해, 전체 파이프라인을 쓴다.
    text, n_ok, n_bad, bad, n_slow = {}, 0, 0, [], 0
    for f in todo:
        r, _ = eng(str(f))
        raw = " ".join(x[1] for x in r) if r else ""
        c = normalize(raw)
        text[f.name] = c
        if raw.strip():
            if c:
                n_ok += 1
            else:
                n_bad += 1
                bad.append(raw)

    # 버린 프레임은 직전 코드를 잇는다
    runs, cur = [], None
    for f in frames:
        idx = int(f.stem.split("_")[1]) - 1
        if f.name in text:
            cur = text[f.name]
        if runs and runs[-1]["chord"] == cur:
            runs[-1]["end"] = idx
        else:
            runs.append({"chord": cur, "start": idx, "end": idx})

    prog = [{"chord": r["chord"],
             "at": round(r["start"] / FPS, 2),
             "dur": round((r["end"] - r["start"] + 1) / FPS, 2)}
            for r in runs if r["chord"]]

    tot = n_ok + n_bad
    rate = n_ok / tot if tot else 0.0
    # 판독 실패 판정: 심볼이 아예 없거나, 성공률이 낮음
    if not prog:
        status = "failed_no_chords"
    elif rate < 0.7:
        status = "failed_low_ocr"
    else:
        status = "ok"

    rec = {
        "id": vid, "title": title,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "status": status,
        "ocr_rate": round(rate, 3),
        "n_frames": len(frames), "n_ocr": len(todo), "n_slow": n_slow,
        "duration_sec": round(len(frames) / FPS, 2),
        "band": bandinfo,
        "progression": prog,
        "unparsed": bad[:20],
    }
    (DONE / f"{vid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(d, ignore_errors=True)          # 프레임 즉시 삭제
    return rec


def playlist_count():
    """재생목록의 실제 곡 수. 실패하면 0."""
    r = subprocess.run(
        YTDLP + ["--flat-playlist", "--print", "%(playlist_count)s",
                 "--playlist-items", "1", PLAYLIST],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return 0


def fetch_playlist(n_vid=None):
    """재생목록을 받는다.

    `-J` 는 100개에서 잘리므로 --print 로 한 줄씩 받는다.
    id 와 title 을 탭으로 갈라 읽는다.
    """
    cmd = YTDLP + ["--flat-playlist", "--print", "%(id)s\t%(title)s"]
    if n_vid:
        cmd += ["--playlist-end", str(n_vid)]
    cmd += [PLAYLIST]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        vid, _, title = line.partition("\t")
        vid = vid.strip()
        if vid and vid != "NA":
            out.append({"id": vid, "title": title.strip()})
    return out


def main():
    n_vid = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "all" else None
    dl_w  = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    oc_w  = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    for p in (WORK, DONE, OUT):
        p.mkdir(exist_ok=True)
    T0 = time.perf_counter()

    # --- 목록 ---
    # 목록 캐시는 전체를 받아온 것만 재사용한다.
    # (시험 실행에서 저장된 일부 목록이 전체 실행을 가로막는 것을 막는다)
    cache = OUT / "playlist_full.json" if n_vid is None else OUT / f"playlist_{n_vid}.json"
    entries = None
    if cache.exists():
        entries = json.loads(cache.read_text(encoding="utf-8"))
        # -J 방식은 100개에서 잘린다. 잘린 캐시를 재사용하지 않도록 검증한다.
        if n_vid is None and len(entries) < playlist_count() * 0.9:
            print(f"[list] cache looks truncated ({len(entries)}), refetching",
                  flush=True)
            entries = None

    if entries is None:
        entries = fetch_playlist(n_vid)
        cache.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    if n_vid:
        entries = entries[:n_vid]
    print(f"[list] {len(entries)} videos", flush=True)

    todo = [e for e in entries if not (DONE / f"{e['id']}.json").exists()]
    print(f"[resume] {len(entries)-len(todo)} already done, {len(todo)} to go", flush=True)

    # --- 배치로 나눠 처리: 다운로드와 OCR을 겹쳐 돌린다 ---
    BATCH = 40
    n_done = 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        t = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=dl_w) as ex:
            list(ex.map(fetch, chunk))
        t_dl = time.perf_counter() - t

        t = time.perf_counter()
        with cf.ProcessPoolExecutor(max_workers=oc_w) as ex:
            for _ in ex.map(process, chunk):
                n_done += 1
        t_oc = time.perf_counter() - t

        el = time.perf_counter() - T0
        rate = el / max(n_done, 1)
        left = (len(todo) - n_done) * rate / 60
        print(f"[{n_done}/{len(todo)}] dl={t_dl:.0f}s ocr={t_oc:.0f}s "
              f"| {rate:.1f}s/video | ETA {left:.0f}min", flush=True)

        # 중간 집계 저장
        write_outputs()

    write_outputs()
    el = time.perf_counter() - T0
    print(f"\n=== done in {el/60:.1f} min ===", flush=True)


def write_outputs():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DONE.glob("*.json"))]
    ok     = [r for r in recs if r.get("status") == "ok"]
    failed = [r for r in recs if r.get("status") != "ok"]
    (OUT / "chords.json").write_text(
        json.dumps(ok, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "failed.json").write_text(
        json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 판독 실패 목록", "",
             f"총 {len(recs)}곡 중 {len(failed)}곡 실패", "",
             "| ID | 사유 | 판독률 | 제목 |", "|---|---|---|---|"]
    for r in failed:
        lines.append(f"| [{r['id']}]({r['url']}) | {r.get('status')} | "
                     f"{r.get('ocr_rate', 0):.0%} | {r['title'][:60]} |")
    (OUT / "failed.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
