"""코드진행 + 제목/아티스트 수집 파이프라인.

usage: run_pipeline.py <N> [dl_workers] [ocr_workers]

단계: 목록 -> 병렬 다운로드+프레임 -> dedup -> 병렬 OCR -> 파싱 -> JSON
"""
import sys, os, re, json, time, subprocess
import concurrent.futures as cf
from pathlib import Path

import numpy as np
from PIL import Image

os.environ["OMP_NUM_THREADS"] = "1"

ROOT   = Path(r"D:\claude\chord-progression-collecting")
WORK   = ROOT / "run"
OUT    = ROOT / "out"
FFMPEG = r"C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
YTDLP  = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]
PLAYLIST = "https://www.youtube.com/playlist?list=UUSHzk0LV3F-MIFS-fGweXhNmQ"

# ---------- 코드 심볼 문법 ----------
RT   = r"[A-G][#b♭♯]?"
TAIL = r"[A-Za-z0-9#b()/♭♯+\-°øΔ, ]*"
PAT  = re.compile(rf"^{RT}\s*{TAIL}$")
SWAP = re.compile(rf"^(.+?)\s+({RT})$")      # "min9(11) G" -> "G min9(11)"

FIXES = [
    (r"\|", ""),                              # 세로 구분선
    (r"\bMajl", "Maj1"),                      # 소문자 L -> 1
    (r"\bminl", "min1"),
    (rf"^({RT})\s+1\s+(?=\d)", r"\1 "),        # "Cb 1 13sus" -> "Cb 13sus"
    (r"\s+", " "),
]


def normalize(s: str):
    """OCR 텍스트 -> 정규 코드 심볼. 실패하면 None."""
    for a, b in FIXES:
        s = re.sub(a, b, s)
    s = s.strip()
    if not s:
        return None
    if PAT.match(s):
        return s
    m = SWAP.match(s)                          # 루트가 뒤로 밀린 경우 복구
    if m:
        cand = f"{m.group(2)} {m.group(1)}"
        if PAT.match(cand):
            return cand
    return None


def dhash(path, size=16):
    a = np.asarray(Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS), dtype=int)
    return (a[:, 1:] > a[:, :-1]).tobytes()


# ---------- 1. 다운로드 + 프레임 ----------
def fetch(item):
    vid = item["id"]
    d = WORK / vid
    d.mkdir(parents=True, exist_ok=True)
    if not list(d.glob("f_*.jpg")):
        subprocess.run(
            YTDLP + ["-f", "bv*/b", "-S", "res:720", "--no-warnings", "-q",
                     "--ffmpeg-location", FFMPEG,
                     "-o", str(d / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True)
        vf = next((p for p in d.glob("v.*")), None)
        if vf is None:
            return vid, 0
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", str(vf),
             "-vf", "fps=1,crop=iw:ih*0.055:0:ih*0.5625,scale=720:-1",
             "-q:v", "3", str(d / "f_%03d.jpg")],
            capture_output=True)
        vf.unlink(missing_ok=True)             # 영상은 즉시 버린다 (디스크 절약)
    return vid, len(list(d.glob("f_*.jpg")))


# ---------- 2. OCR ----------
def ocr_batch(paths):
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    res = {}
    for p in paths:
        r, _ = engine(str(p))
        res[str(p)] = " ".join(x[1] for x in r) if r else ""
    return res


def main():
    n_vid = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    dl_w  = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    oc_w  = int(sys.argv[3]) if len(sys.argv) > 3 else 6

    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    T0 = time.perf_counter()

    # --- 목록 (제목/아티스트/장르 포함) ---
    t = time.perf_counter()
    r = subprocess.run(
        YTDLP + ["--flat-playlist", "-J", "--playlist-end", str(n_vid), PLAYLIST],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    entries = [{"id": e["id"], "title": e.get("title", "")} for e in json.loads(r.stdout)["entries"]]
    t_list = time.perf_counter() - t
    print(f"[1/4] list: {len(entries)} videos in {t_list:.1f}s", flush=True)

    # --- 다운로드 + 프레임 ---
    t = time.perf_counter()
    counts = {}
    with cf.ThreadPoolExecutor(max_workers=dl_w) as ex:
        for vid, n in ex.map(fetch, entries):
            counts[vid] = n
    t_dl = time.perf_counter() - t
    nf = sum(counts.values())
    print(f"[2/4] fetch: {nf} frames in {t_dl:.1f}s ({t_dl/len(entries):.2f}s/video)", flush=True)

    # --- dedup ---
    t = time.perf_counter()
    keep = {}
    for e in entries:
        d = WORK / e["id"]
        prev, ks = None, []
        for f in sorted(d.glob("f_*.jpg")):
            h = dhash(f)
            if h != prev:
                ks.append(f)
            prev = h
        keep[e["id"]] = ks
    allk = [p for v in keep.values() for p in v]
    t_dd = time.perf_counter() - t
    print(f"[3/4] dedup: {nf} -> {len(allk)} ({len(allk)/max(nf,1)*100:.0f}%) in {t_dd:.1f}s", flush=True)

    # --- OCR ---
    t = time.perf_counter()
    chunks = [allk[i::oc_w] for i in range(oc_w)]
    texts = {}
    with cf.ProcessPoolExecutor(max_workers=oc_w) as ex:
        for part in ex.map(ocr_batch, chunks):
            texts.update(part)
    t_ocr = time.perf_counter() - t
    print(f"[4/4] ocr: {len(allk)} frames in {t_ocr:.1f}s ({t_ocr/max(len(allk),1)*1000:.0f}ms/frame)", flush=True)

    # --- 파싱 + 저장 ---
    records, n_ok, n_bad, bad = [], 0, 0, []
    for e in entries:
        seq, raws = [], []
        for p in keep[e["id"]]:
            raw = texts.get(str(p), "")
            if not raw.strip():
                continue
            c = normalize(raw)
            if c:
                n_ok += 1
                if not seq or seq[-1] != c:
                    seq.append(c)
            else:
                n_bad += 1
                bad.append({"video": e["id"], "raw": raw})
            raws.append(raw)
        records.append({
            "id": e["id"],
            "title": e["title"],
            "url": f"https://www.youtube.com/watch?v={e['id']}",
            "progression": seq,
            "n_frames": counts.get(e["id"], 0),
            "n_unique": len(keep[e["id"]]),
        })

    (OUT / "chords.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "unparsed.json").write_text(
        json.dumps(bad, ensure_ascii=False, indent=2), encoding="utf-8")

    total = time.perf_counter() - T0
    tot_sym = n_ok + n_bad
    print(f"\n=== {len(entries)} videos in {total:.1f}s ({total/len(entries):.2f}s/video) ===")
    print(f"  symbols: {n_ok} ok / {n_bad} unparsed = {n_ok/max(tot_sym,1)*100:.1f}%")
    print(f"  projected 1478: {total/len(entries)*1478/60:.1f} min")
    print(f"  -> {OUT/'chords.json'}")


if __name__ == "__main__":
    main()
