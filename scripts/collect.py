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
DATA   = ROOT / "data"          # 저장소에 올라가는 결과물
PUBLISH = os.environ.get("NO_PUBLISH") != "1"   # 배치마다 저장소에 반영
MIN_EXPECTED = 200      # 전체 실행 시 이 이하면 목록이 잘린 것으로 본다
BAD_ABORT    = 0.5      # 한 배치 실패율이 이 이상이면 경고, 두 번 연속이면 중단
DL_MAX       = 4        # 다운로드 병렬 상한. 이보다 크게 넣어도 4로 깎인다
OCR_MAX      = 4        # 판독 병렬 상한. 6코어에서 컴퓨터를 쓸 수 있는 선
FFMPEG = r"C:\Users\inbm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
YTDLP  = [r"C:\Users\inbm\.local\bin\uvx.exe", "yt-dlp"]

# yt-dlp 는 기본적으로 콘솔 코드페이지(cp949)로 내보내, 제목의 유니코드
# 따옴표와 이모지를 변환 불가 문자로 바꿔버린다. 원본 그대로 받으려면
# UTF-8 출력을 강제해야 한다.
ENV_UTF8 = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
# 채널의 업로드 재생목록(UU...)은 100개까지만 내주고 그 뒤 페이지를 막는다.
# playlist_count 는 1578 이라 답하지만 101번째 항목부터 존재하지 않는다.
# 채널 쇼츠 탭으로 접근해야 1479개 전부를 받을 수 있다.
PLAYLIST = "https://www.youtube.com/channel/UCzk0LV3F-MIFS-fGweXhNmQ/shorts"

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

# 글자를 잘못 읽은 것 중 규칙으로 확실히 잡히는 것.
# (찾을 것, 바꿀 것, 확신) — 확신이 False 면 결과에 물음표가 붙는다.
TYPOS = [
    (r"\bMai\b",        "Maj",   True),   # j 를 i 로 읽음
    (r"\bMai(?=[0-9(])", "Maj",  True),
    (r"\bmaior\b",      "Maj",   True),
    (r"\bminor\s*7th\b", "min7", True),   # 영어를 기호로
    (r"\bmajor\s*7th\b", "Maj7", True),
    # '3rd minor' 는 음정 표기다. minor -> min 보다 먼저 순서를 바로잡는다.
    (r"(\d+)(?:st|nd|rd|th)\s+minor\b", r"min \1rd", True),
    (r"(\d+)(?:st|nd|rd|th)\s+major\b", r"Major \1rd", True),
    (r"\bminor\b",      "min",   True),
    (r"\bmajor\b",      "Maj",   True),
    (r"\(\s*\(", "(",            True),   # 괄호가 겹침
    (r"\)\s*\)", ")",            True),
    (r"\bl(?=[0-9])",   "1",     True),   # 소문자 L 을 1 로
    (r"\bO(?=[0-9])",   "0",     True),
    # 글자 사이에 낀 1 — 세로선을 숫자로 읽은 것
    (r"(?<=[A-Za-z])1(?=[a-z])", "", True),      # AM1aj -> AMaj
    # 괄호가 겹쳐 열린 것 — '(c (add3)' / '(o (add2)' -> '(add3)' / '(add2)'
    # 괄호와 글자 사이에 공백이 끼는 경우가 있다.
    (r"\(\s*[A-Za-z]?\s*\((?=[a-z])", "(", True),
    # 괄호 뒤에 낀 숫자 — 'Maj13( 3(#11)' -> 'Maj13(#11)'
    (r"\(\s*\d+\s*\((?=[#b])", "(", True),
    # Maj·min 뒤에 낀 3 — Maj313 -> Maj13
    (r"\b(Maj|min)3(?=1[0-9])", r"\1", True),

    # 근음 바로 뒤에 낀 3 — 화면 세로선을 숫자로 읽은 것.
    # 뒤에 글자나 / 가 오는 것만. 'B3' 처럼 끝나면 코드일 수 있다.
    (rf"^({RT})\s*3(?=\s*(Maj|min|dim|aug|sus|/|\d))", r"\1 ", True),
    # 근음 뒤에 낀 1 — 'C1 13sus' 처럼 근음과 확장음 사이에 홀로 선 1.
    # 1 뒤에 반드시 공백이 있어야 한다. F#13sus 는 정상이므로 건드리지 않는다.
    (rf"^({RT})1\s+(?=\d)", r"\1 ", True),         # C1 13sus -> C 13sus
    (rf"^({RT})\s+1(?=1[13])", r"\1 ", True),      # C 113 -> C 13
    (rf"^({RT})\s+1(?=[2-9]\s*$)", r"\1 ", True),  # C 19 -> C 9
    # min 뒤에 낀 1 — min17 -> min11, min19 -> min9
    (r"\bmin17\b",      "min11", True),
    (r"\bmin19\b",      "min9",  True),
    # 'min9 11' 처럼 확장음이 둘 나열된 것 — 높은 쪽만 남긴다
    (r"\b(min|Maj)(\d+)\s+(\d+)\b", r"\1\3", True),
    # 1l 은 11 — 소문자 L 을 1 로 읽은 것. min9(1l) / Maj9#1l
    (r"1l\b",           "11",    True),
    (r"1l(?=[)\s])",    "11",    True),
    # 괄호 안 홀로 선 1 은 11 이 잘린 것. min7(1) -> min7(11)
    (r"\((1)\)",        r"(11)", True),
    (r"\(#1\)",         "(#11)", True),
    # 코드 끝에 떨어진 1 도 같다. 'A min7 1' -> 'A min7(11)'
    # n.c. 뒤에 붙은 것은 잡음이므로 그냥 뗀다.
    (r"(n\.?c\.?)[\s0-9]+$", r"\1", True),
    (r"\s+1\s*$",       "(11)",  True),
    (r"\s+11\s*$",      "(11)",  True),
    # 근음 뒤 홀로 선 0 — Eb 0 min(add2) -> Eb min(add2)
    (rf"^({RT})\s+0\s+", r"\1 ", True),
    # Fb 는 쓰지 않는다. E 를 잘못 읽은 것이다. (Cb 는 Gb 장조의 4도로 쓰인다)
    (r"^Fb(?![a-z])",   "E",     True),
    (r"/\s*Fb\b",       "/E",    True),
    # 끝에 떨어진 음이름은 베이스다. 슬래시가 안 읽힌 것.
    #   'D# min7(4) C#' -> 'D# min7(4) / C#'
    (rf"(?<=[)\d])\s+({RT})\s*$", r" / \1", True),
    # #1l9 의 l 은 1 오독. #11 은 그대로 두어야 하므로 뒤가 1 이 아닐 때만.
    # 근음의 # (F#13sus) 는 건드리면 안 되므로 앞에 글자가 있을 때만 본다.
    (r"(?<=[a-z])#1l(?=\d)", "#11", True),       # Maj#1l9 -> Maj#119
    (r"(?<=[a-z])#1(?=[02-9])", "#11", True),    # Maj#19 -> Maj#119
    (r"(?<=[a-z])l(?=\d)", "1",   True),         # Majl3 -> Maj13
    # min 뒤에 붙은 s — 판독 잡음
    (r"\bmins\b",       "min",   True),
    (r"(?<=min)s(?=\d)", "",     True),          # mins11 -> min11
    # 같은 숫자가 붙어 나온 것 — 한 번 잡힌 것이 두 번 읽혔다
    (r"\b99\b",         "9",     True),
    (r"\b1111\b",       "11",    True),
    (r"\b1313\b",       "13",    True),
    # 같은 숫자가 두 번 — 공백이 끼어 있어도 잡는다.
    # Maj9 9 -> Maj9. \b 는 Maj9 의 9 앞에서 안 걸리므로 숫자 경계만 본다.
    (r"(?<!\d)(\d{1,2})\s+\1(?!\d)", r"\1", True),
    (r"(?<=Maj)99",     "9",     True),          # FMaj99 -> FMaj9
    (r"(?<=min)99",     "9",     True),
]

# 앞뒤를 봐야 아는 것 — 고치되 물음표를 붙인다
UNSURE = [
    (r"\bPerfect\s*[45](th)?\b", None),   # 코드가 아니라 두 음
    (r"\bOctave\b",              None),
    (r"\bTritone\b",             None),
]


def fix_typos(s):
    """글자 오독을 고친다. (고친 문자열, 확신) 를 돌려준다."""
    out, sure = s, True
    for pat, rep, ok in TYPOS:
        new = re.sub(pat, rep, out)
        if new != out:
            out = new
            sure = sure and ok
    return out, sure


# 코드에 쓸 수 있는 숫자. 이것 말고 다른 값이 나오면 겹쳐 읽힌 것이다.
#   D9sus4  -> 9, 4   둘 다 정상
#   Cb57    -> 57     없는 값. 5 와 7 이 붙었다
#   A99     -> 99     없는 값. 9 가 두 번 잡혔다
OK_NUMS = {"2", "4", "5", "6", "7", "9", "11", "13"}


def looks_odd(std):
    """표준 표기가 흐트러졌는지 본다. 판독이 어긋난 자리를 찾는다."""
    if not std:
        return False
    tail = re.sub(rf"^{RT}", "", std)
    nums = re.findall(r"\d+", re.sub(r"\([^)]*\)", "", tail))
    # 음정 표기(Octave·Perfect 5th·Major 3rd)는 화면에 실제로 그렇게
    # 적혀 있다. 코드가 아닐 뿐 판독이 틀린 것이 아니므로 물음표를 안 붙인다.
    if re.search(r"(Octave|Tritone|\d(st|nd|rd|th))$", std, re.I):
        return False
    # N.C. 는 코드 없음 표시다. 음이 끌리는 구간이라 판독 오류가 아니다.
    if re.search(r"N\.?C\.?", std, re.I):
        return False
    return bool(std.count("(") != std.count(")")
                or any(n not in OK_NUMS for n in nums)
                or re.search(r"\d\s+\d", std))


# 코드를 부분으로 가른다. "Db Maj(add2) / F" -> root Db, quality Maj(add2), bass F
SPLIT = re.compile(rf"^({RT})\s*(.*?)(?:\s*/\s*({RT}))?$")

# 음이름을 반음 번호로. 조옮김·화성 분석에 쓴다.
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pitch_class(root: str):
    """'Db' -> 1. 못 읽으면 None."""
    if not root:
        return None
    n = PC.get(root[0].upper())
    if n is None:
        return None
    for ch in root[1:]:
        if ch in "#♯":
            n += 1
        elif ch in "b♭":
            n -= 1
    return n % 12


# ---------- 조성 판정 ----------
# 화면에 조성이 없으므로 코드에서 짚어낸다.
# 각 코드가 내는 음을 모아, 24개 조(장조 12 + 단조 12) 중 어디에 가장
# 잘 들어맞는지 본다. 지속 시간으로 가중치를 준다 — 오래 울린 코드가
# 조를 더 강하게 정한다.

MAJOR_SET = [0, 2, 4, 5, 7, 9, 11]
MINOR_SET = [0, 2, 3, 5, 7, 8, 10]        # 자연단음계
NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F",
               "F#", "G", "G#", "A", "A#", "B"]
NAMES_FLAT  = ["C", "Db", "D", "Eb", "E", "F",
               "Gb", "G", "Ab", "A", "Bb", "B"]


def chord_tones(root_pc, qual):
    """코드가 내는 음을 근음으로부터의 반음 수로 돌려준다."""
    if root_pc is None:
        return []
    q = (qual or "").lower().replace(" ", "")
    t = [0]

    # 3음
    if "sus4" in q or q.startswith("sus"):
        t.append(5)
    elif "sus2" in q:
        t.append(2)
    elif "min" in q or q.startswith("m") and not q.startswith("maj"):
        t.append(3)
    elif "dim" in q:
        t.append(3)
    else:
        t.append(4)

    # 5음
    if "b5" in q or "dim" in q:
        t.append(6)
    elif "#5" in q or "aug" in q:
        t.append(8)
    elif "no5" not in q:
        t.append(7)

    # 7음
    if "maj7" in q or "maj9" in q or "maj13" in q or "maj11" in q:
        t.append(11)
    elif "dim7" in q:
        t.append(9)
    elif "7" in q or "9" in q or "11" in q or "13" in q or "alt" in q:
        t.append(10)

    # 확장음 — 변화음은 조 판정을 흐리므로 자연음만 센다
    if "9" in q and "b9" not in q and "#9" not in q:
        t.append(2)
    if "11" in q and "#11" not in q:
        t.append(5)
    if "13" in q and "b13" not in q:
        t.append(9)
    if "6" in q:
        t.append(9)

    return [(root_pc + x) % 12 for x in t]


def detect_key(prog):
    """진행에서 조성을 짚는다. (표기, 확신도 0~1) 를 돌려준다."""
    if not prog:
        return None, 0.0

    weight = [0.0] * 12
    root_w = [0.0] * 12
    for p in prog:
        pc = p.get("pc")
        if pc is None:
            continue
        d = float(p.get("dur") or 0.25)
        root_w[pc] += d
        for t in chord_tones(pc, p.get("quality")):
            weight[t] += d

    total = sum(weight)
    if total <= 0:
        return None, 0.0

    # 곡은 대개 으뜸음으로 시작하거나 끝난다. 그 자리를 따로 본다.
    pcs = [p.get("pc") for p in prog if p.get("pc") is not None]
    first_pc = pcs[0] if pcs else None
    last_pc = pcs[-1] if pcs else None

    # 가장 오래 울린 근음도 으뜸음일 가능성이 높다
    rw_total = sum(root_w) or 1.0
    longest_pc = max(range(12), key=lambda i: root_w[i])

    best = []
    for tonic in range(12):
        for is_minor, scale in ((0, MAJOR_SET), (1, MINOR_SET)):
            inside = sum(weight[(tonic + s) % 12] for s in scale)
            score = inside / total
            # 으뜸음을 근음으로 쓴 코드가 많으면 그 조일 가능성이 높다
            score += 0.30 * (root_w[tonic] / rw_total)
            # 딸림음(5도)도 조를 가리킨다
            score += 0.10 * (root_w[(tonic + 7) % 12] / rw_total)
            # 시작·끝·최장 근음이 으뜸음이면 더 확실하다
            if tonic == first_pc:
                score += 0.12
            if tonic == last_pc:
                score += 0.08
            if tonic == longest_pc:
                score += 0.12
            best.append((score, tonic, is_minor))

    best.sort(reverse=True)
    top, second = best[0], best[1]
    score, tonic, is_minor = top

    # 이름은 화면에 쓰인 표기를 따른다. b 가 많으면 플랫 이름으로.
    flats = sum(1 for p in prog if "b" in (p.get("root") or ""))
    sharps = sum(1 for p in prog if "#" in (p.get("root") or ""))
    names = NAMES_FLAT if flats >= sharps else NAMES_SHARP
    label = names[tonic] + (" minor" if is_minor else " major")

    # 확신도 — 1등과 2등의 차이가 크면 확신이 높다
    gap = score - second[0]
    conf = max(0.0, min(1.0, gap * 6))
    return label, round(conf, 2)


# ---------- 표준 표기로 바꾸기 ----------
# 이 채널은 손가락으로 짚은 음을 그대로 적는다.
#   화면 A 9(13)#11  ->  표준 A13(#11)
#   화면 E min7(11)  ->  표준 Emin11
# 리드시트 관례는 자연음 확장(9·11·13) 중 가장 높은 것만 밖에 쓰고,
# 변화음(#11·b9 등)을 괄호에 모으는 것이다.

# 자연음 확장. min9 처럼 글자에 붙어 있어도 잡아야 하므로 \b 를 쓰지 않는다.
# 앞에 #·b 가 붙은 것(변화음)과 13 의 1 을 11 로 잘못 읽는 것을 막는다.
NAT_EXT = re.compile(r"(?<![#b\d])(13|11|9|6|4|2)(?!\d)")
ALT_EXT = re.compile(r"([#b])(5|9|11|13)")               # 변화음
QUAL_HEAD = re.compile(
    r"^(Maj|maj|M|min|m|dim|aug|sus|°|ø|\+|-)?", re.I)


def to_standard(root, qual, bass):
    """제작자 표기를 리드시트 표기로 바꾼다. 못 바꾸면 원문 그대로."""
    if not root:
        return None
    if not qual:
        return root + (f"/{bass}" if bass else "")

    q = qual.replace(" ", "")

    # 손대지 않는 것 — 이미 표준이거나 규칙 밖이다
    if re.fullmatch(r"(7alt|alt|N\.C\.)", q, re.I):
        return f"{root}{q}" + (f"/{bass}" if bass else "")

    # 음정 표기 — 코드가 아니라 두 음. 읽기 좋게 띄운다.
    # 서수(3rd·5th)로 끝나거나 Octave·Tritone 인 것만이다.
    m = re.fullmatch(
        r"(Octave|Tritone|(?:Perfect|Major|Minor|min|maj)\s*\d+(?:st|nd|rd|th))",
        q, re.I)
    if m:
        t = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", m.group(1))
        return f"{root} {t}" + (f"/{bass}" if bass else "")

    # add 는 확장음이 아니라 덧붙인 음이다. 괄호를 살려 그대로 둔다.
    if re.search(r"add", q, re.I):
        return f"{root}{q}" + (f"/{bass}" if bass else "")

    # no3·no5 같은 생략 표시는 따로 떼어 맨 뒤에 붙인다.
    # 그냥 두면 확장음 사이에 끼어 AbMajno39(#11) 처럼 된다.
    omits = re.findall(r"no\s*([0-9]+)", q, re.I)
    q = re.sub(r"\(?\s*no\s*[0-9]+\s*\)?", "", q, flags=re.I)

    # sus 를 먼저 떼어낸다. sus4 의 4 는 확장음이 아니다.
    sus = ""
    m = re.search(r"sus\s*([24])?", q, re.I)
    if m:
        sus = "sus" + (m.group(1) or "")
        q = q[:m.start()] + q[m.end():]

    alts = ["".join(x) for x in ALT_EXT.findall(q)]
    nats = [int(n) for n in NAT_EXT.findall(ALT_EXT.sub("", q))]

    # 화음 성질 — min·Maj·dim 등
    body = ALT_EXT.sub("", q)
    body = NAT_EXT.sub("", body)
    body = re.sub(r"[()]", "", body).strip()

    has7 = "7" in body
    body = body.replace("7", "").strip()

    # 괄호 안 4 는 한 옥타브 위에서 11 이다. min7(4) -> min11
    # sus4 의 4 는 다르므로 sus 를 떼어낸 뒤에 본다.
    if not sus:
        nats = [11 if x == 4 else x for x in nats]

    # 자연음 확장은 가장 높은 것만 남긴다
    top = max(nats) if nats else None
    if top is None and has7:
        top = 7

    out = root + body
    if top:
        out += str(top)
    out += sus
    if alts:
        out += "(" + "".join(alts) + ")"
    for o in omits:
        out += f"(no{o})"
    if bass:
        out += f"/{bass}"
    return out


def split_chord(c: str):
    """코드 문자열을 root/quality/bass 로 가른다."""
    m = SPLIT.match(c)
    if not m:
        return {"root": None, "quality": None, "bass": None,
                "pc": None, "std": None}
    root, qual, bass = m.group(1), (m.group(2) or "").strip(), m.group(3)
    return {
        "root": root,
        "quality": qual or None,
        "bass": bass,
        "pc": pitch_class(root),
        "std": to_standard(root, qual, bass),
    }


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
    r = subprocess.run(
        YTDLP + ["-f", "bv*/b", "-S", "res:720", "--no-warnings", "-q",
                 "--ffmpeg-location", FFMPEG,
                 "-o", str(d / "v.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=ENV_UTF8)
    vf = next((p for p in d.glob("v.*")), None)
    if vf is None:
        # 실패 이유를 남긴다. 조용히 넘어가면 도구가 깨져도 알 수 없다.
        err = (r.stderr or r.stdout or "").strip()[:300]
        (d / "dl_error.txt").write_text(
            f"rc={r.returncode}\n{err}\n", encoding="utf-8")
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


def join_boxes(r, img_h=None):
    """판독된 글자 조각을 코드 심볼만 골라 왼쪽→오른쪽 순으로 붙인다.

    두 가지를 바로잡는다.

    1. 순서 — 글자가 크면 한 코드가 여러 조각으로 쪼개지는데, 판독기가
       돌려주는 순서는 화면 순서가 아니다. 그대로 붙이면 'B min9(11)' 이
       '9 (11) B mins' 로 뒤집힌다.

    2. 잡음 — 크롭이 위로 조금 넘치면 영상 제목 자막이 함께 들어온다.
       코드 심볼은 크롭 하단에 붙어 있고 자막은 위쪽에 뜨므로,
       아래끝이 하단에 닿는 조각만 남긴다.
    """
    if not r:
        return ""

    items = []
    for x in r:
        box, txt = x[0], x[1]
        try:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            items.append((min(xs), max(ys), txt))
        except Exception:
            items.append((0.0, None, txt))

    # 아래끝이 가장 낮은 조각을 기준으로, 그와 비슷한 높이의 것만 쓴다.
    bottoms = [b for _, b, _ in items if b is not None]
    if bottoms:
        base = max(bottoms)
        h = img_h or base
        tol = max(h * 0.25, 8)
        items = [it for it in items
                 if it[1] is None or (base - it[1]) <= tol]

    items.sort(key=lambda t: t[0])
    return " ".join(t for _, _, t in items)


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
        ep = d / "dl_error.txt"
        why = ep.read_text(encoding="utf-8").strip() if ep.exists() else ""
        rec = {"id": vid, "title": title, "url": f"https://www.youtube.com/watch?v={vid}",
               "status": "no_frames", "error": why[:300], "progression": []}
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
    frame_h = Image.open(frames[0]).size[1]
    text, n_ok, n_bad, bad, n_slow = {}, 0, 0, [], 0
    for f in todo:
        r, _ = eng(str(f))
        raw = join_boxes(r, frame_h)
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

    prog = []
    for r in runs:
        if not r["chord"]:
            continue
        raw = r["chord"]
        fixed, sure = fix_typos(raw)
        item = {"chord": raw,          # 화면에서 읽은 그대로
                "at": round(r["start"] / FPS, 2),
                "dur": round((r["end"] - r["start"] + 1) / FPS, 2)}
        item.update(split_chord(fixed))
        if fixed != raw:
            item["fixed"] = True

        # 자신 없는 것에 물음표를 붙인다. 보는 쪽이 알아야 한다.
        std = item.get("std") or ""
        if looks_odd(std) or not sure:
            item["unsure"] = True
            if std:
                item["std"] = std + " (?)"
        prog.append(item)

    tot = n_ok + n_bad
    rate = n_ok / tot if tot else 0.0
    # 판독 실패 판정: 심볼이 아예 없거나, 성공률이 낮음
    if not prog:
        status = "failed_no_chords"
    elif rate < 0.7:
        status = "failed_low_ocr"
    else:
        status = "ok"

    # 확신이 낮으면 물음표를 붙인다. 보는 쪽이 추측인 줄 알아야 한다.
    key_label, key_conf = detect_key(prog)
    if key_label and key_conf < 0.5:
        key_label += " (?)"

    rec = {
        "id": vid, "title": title,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "status": status,
        "ocr_rate": round(rate, 3),
        "n_frames": len(frames), "n_ocr": len(todo), "n_slow": n_slow,
        "duration_sec": round(len(frames) / FPS, 2),
        "key": key_label,
        "key_confidence": key_conf,
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
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=ENV_UTF8)
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
                       encoding="utf-8", errors="replace", env=ENV_UTF8)
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
    # 다운로드를 8개씩 돌리면 포트가 모자라 새 연결을 못 만드는 일이 있다.
    # (2026-09-03 밤 Tcpip 4231) 판독이 병목이라 4로 낮춰도 전체 속도는 같다.
    dl_w  = min(int(sys.argv[2]) if len(sys.argv) > 2 else 4, DL_MAX)
    oc_w  = min(int(sys.argv[3]) if len(sys.argv) > 3 else 3, OCR_MAX)

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
        # 100개에서 잘린 캐시를 재사용하지 않도록 막는다.
        if n_vid is None and len(entries) <= MIN_EXPECTED:
            print(f"[list] cache looks truncated ({len(entries)}), refetching",
                  flush=True)
            entries = None

    if entries is None:
        entries = fetch_playlist(n_vid)
        cache.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    if n_vid:
        entries = entries[:n_vid]
    print(f"[list] {len(entries)} videos", flush=True)

    # 전체 실행인데 목록이 잘렸다면 여기서 멈춘다.
    # 100곡만 처리하고 끝나는 사고를 막는다.
    if n_vid is None and len(entries) <= MIN_EXPECTED:
        print(f"[list] ABORT: only {len(entries)} videos — playlist truncated.\n"
              f"       채널 탭 주소를 쓰고 있는지 확인이 필요합니다.", flush=True)
        return

    todo = [e for e in entries if not (DONE / f"{e['id']}.json").exists()]
    print(f"[resume] {len(entries)-len(todo)} already done, {len(todo)} to go", flush=True)

    # --- 배치로 나눠 처리: 다운로드와 OCR을 겹쳐 돌린다 ---
    BATCH = 40
    n_done = 0
    n_streak = 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        t = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=dl_w) as ex:
            list(ex.map(fetch, chunk))
        t_dl = time.perf_counter() - t

        t = time.perf_counter()
        n_bad = n_dead = 0
        with cf.ProcessPoolExecutor(max_workers=oc_w) as ex:
            for rec in ex.map(process, chunk):
                n_done += 1
                st = rec.get("status")
                if st != "ok":
                    n_bad += 1
                # 고장 판정은 다운로드 실패만 센다.
                # 이 채널에는 코드 화면이 없는 홍보·잡담 영상이 섞여 있어
                # 판독 실패는 정상적인 결과일 수 있다.
                if st == "no_frames":
                    n_dead += 1
        t_oc = time.perf_counter() - t

        el = time.perf_counter() - T0
        rate = el / max(n_done, 1)
        left = (len(todo) - n_done) * rate / 60
        dead_rate = n_dead / len(chunk)
        print(f"[{n_done}/{len(todo)}] dl={t_dl:.0f}s ocr={t_oc:.0f}s "
              f"| {rate:.1f}s/video | 실패 {n_bad}/{len(chunk)} "
              f"(다운로드 실패 {n_dead}) | ETA {left:.0f}min", flush=True)

        # 도구가 깨지면 다운로드가 조용히 실패하며 빈 결과만 쌓인다.
        # 한 배치가 통째로 무너지면 그 뒤는 전부 낭비이므로 즉시 멈춘다.
        if dead_rate >= BAD_ABORT:
            n_streak += 1
            print(f"[warn] 다운로드 실패율 {dead_rate:.0%} "
                  f"({n_streak}회 연속)", flush=True)
            if n_streak >= 2:
                print(f"[ABORT] 두 배치 연속 다운로드 실패율 "
                      f"{BAD_ABORT:.0%} 이상.\n"
                      f"        다운로드 도구가 깨졌을 수 있습니다.\n"
                      f"        확인: uvx yt-dlp --version", flush=True)
                write_outputs()
                publish()
                return
        else:
            n_streak = 0

        # 중간 집계 저장 + 저장소 반영
        write_outputs()
        publish()

    write_outputs()
    publish()
    el = time.perf_counter() - T0
    print(f"\n=== done in {el/60:.1f} min ===", flush=True)


def publish():
    """진행분을 저장소에 올린다. 실패해도 수집은 계속한다."""
    if not PUBLISH:
        return
    try:
        r = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "publish.py")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300)
        out = (r.stdout or "").strip()
        if out:
            print(f"[publish] {out}", flush=True)
    except Exception as e:
        print(f"[publish] skipped: {e}", flush=True)


def write_outputs():
    """결과를 모아 쓴다.

    본체는 JSONL(한 줄에 한 곡)이다. 20MB 짜리 JSON 배열은 끝까지 읽어야
    파싱이 되지만, JSONL 은 몇 줄만 잘라 읽어도 그 자체로 완결된다.
    읽어가는 쪽(사람이든 도구든)이 필요한 만큼만 가져갈 수 있다.
    """
    DATA.mkdir(exist_ok=True)
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DONE.glob("*.json"))]
    ok     = [r for r in recs if r.get("status") == "ok"]
    failed = [r for r in recs if r.get("status") != "ok"]

    with (DATA / "chords.jsonl").open("w", encoding="utf-8") as f:
        for r in ok:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with (DATA / "failed.jsonl").open("w", encoding="utf-8") as f:
        for r in failed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 목차 — 전체를 읽지 않고도 무엇이 들어 있는지 훑을 수 있게 한다.
    index = {
        "count": len(recs),
        "ok": len(ok),
        "failed": len(failed),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "songs": [{"id": r["id"], "title": r["title"],
                   "n_chords": len(r.get("progression", [])),
                   "duration_sec": r.get("duration_sec"),
                   "key": r.get("key"),
                   "key_confidence": r.get("key_confidence"),
                   "n_unsure": sum(1 for p in r.get("progression", [])
                                   if p.get("unsure")),
                   "status": r.get("status")}
                  for r in recs],
    }
    (DATA / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 판독 실패 목록", "",
             f"총 {len(recs)}곡 중 {len(failed)}곡 실패", "",
             "| ID | 사유 | 판독률 | 제목 |", "|---|---|---|---|"]
    for r in failed:
        lines.append(f"| [{r['id']}]({r['url']}) | {r.get('status')} | "
                     f"{r.get('ocr_rate', 0):.0%} | {r['title'][:60]} |")
    (OUT / "failed.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
