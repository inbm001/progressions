"""이미 뽑아 둔 결과에 조성·표준표기·오자수정을 다시 입힌다.

영상을 새로 받지 않는다. done/*.json 의 코드 문자열만 다시 처리한다.

usage: rebuild.py
"""
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import (FPS, DONE, split_chord, fix_typos, looks_odd,
                     detect_key)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def redo(rec):
    prog = []
    for p in rec.get("progression", []):
        raw = p.get("chord")
        if not raw:
            continue
        fixed, sure = fix_typos(raw)
        item = {"chord": raw, "at": p["at"], "dur": p["dur"]}
        item.update(split_chord(fixed))
        if fixed != raw:
            item["fixed"] = True
        std = item.get("std") or ""
        if looks_odd(std) or not sure:
            item["unsure"] = True
            if std:
                item["std"] = std + " (?)"
        prog.append(item)

    key, conf = detect_key(prog)
    if key and conf < 0.5:
        key += " (?)"
    rec["progression"] = prog
    rec["key"] = key
    rec["key_confidence"] = conf
    return rec


def main():
    files = sorted(DONE.glob("*.json"))
    n = 0
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("status") != "ok":
            continue
        f.write_text(json.dumps(redo(rec), ensure_ascii=False),
                     encoding="utf-8")
        n += 1
    print(f"{n}곡 갱신")


if __name__ == "__main__":
    main()
