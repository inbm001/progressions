"""수집 결과를 웹페이지가 읽을 형태로 내보낸다.

docs/
  index.html          — 목록과 상세를 한 파일에서 처리
  data/index.json     — 곡 목록. 가볍다
  data/songs/<id>.json — 곡 하나. 고를 때만 받는다

usage: build_site.py
"""
import sys, json, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import DONE, ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCS = ROOT / "docs"
OUT_DATA = DOCS / "data"
OUT_SONGS = OUT_DATA / "songs"


def clean_title(t):
    """제목에서 해시태그와 이모지 꼬리를 걷어낸다."""
    import re
    t = re.sub(r"#\w+", "", t)
    t = re.sub(r"[🔥🎹✨🎵🎶💥⚡️]+", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" -·|")


def split_title(t):
    """'Artist "Song" Chords ...' 에서 아티스트와 곡명을 갈라낸다."""
    import re
    m = re.match(r'^(.+?)\s*[""“”"]([^""“”"]+)[""“”"]', t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def main():
    if OUT_SONGS.exists():
        shutil.rmtree(OUT_SONGS)
    OUT_SONGS.mkdir(parents=True, exist_ok=True)

    songs = []
    for f in sorted(DONE.glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("status") != "ok":
            continue

        title = clean_title(rec.get("title", ""))
        artist, song = split_title(title)
        conf = rec.get("key_confidence") or 0.0

        (OUT_SONGS / f"{rec['id']}.json").write_text(
            json.dumps(rec, ensure_ascii=False), encoding="utf-8")

        songs.append({
            "id": rec["id"],
            "title": title,
            "artist": artist,
            "song": song,
            "key": rec.get("key"),
            "conf": conf,
            "dur": rec.get("duration_sec"),
            "n": len(rec.get("progression", [])),
            "unsure": sum(1 for p in rec.get("progression", [])
                          if p.get("unsure")),
        })

    # 확신 묶음 — 높음 0.7 이상, 보통 0.4~0.7, 낮음 0.4 미만
    for s in songs:
        c = s["conf"]
        s["band"] = "high" if c >= 0.7 else ("mid" if c >= 0.4 else "low")

    import time
    idx = {
        "count": len(songs),
        "updated": time.strftime("%Y-%m-%d %H:%M"),
        "bands": {
            "high": sum(1 for s in songs if s["band"] == "high"),
            "mid":  sum(1 for s in songs if s["band"] == "mid"),
            "low":  sum(1 for s in songs if s["band"] == "low"),
        },
        "songs": songs,
    }
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "index.json").write_text(
        json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    print(f"{len(songs)}곡")
    print(f"  확신 높음 {idx['bands']['high']}")
    print(f"  확신 보통 {idx['bands']['mid']}")
    print(f"  확신 낮음 {idx['bands']['low']}")


if __name__ == "__main__":
    main()
