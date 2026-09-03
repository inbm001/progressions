"""수집 결과를 저장소에 올린다.

usage: publish.py [메시지]

data/ 에 변화가 없으면 아무것도 하지 않는다.
밤 실행 중 주기적으로 불러도 안전하다.
"""
import sys, json, subprocess
from pathlib import Path

ROOT = Path(r"D:\claude\chord-progression-collecting")
DATA = ROOT / "data"


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(args),
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(f"[git] {' '.join(args)} -> {r.returncode}\n{r.stderr}", flush=True)
    return r


def main():
    idx = DATA / "index.json"
    if not idx.exists():
        print("no data yet", flush=True)
        return

    info = json.loads(idx.read_text(encoding="utf-8"))
    n, ok, failed = info["count"], info["ok"], info["failed"]

    git("add", "-A")
    if not git("diff", "--cached", "--quiet", check=False).returncode:
        print("nothing to commit", flush=True)
        return

    msg = sys.argv[1] if len(sys.argv) > 1 else (
        f"{n}곡 수집 (정상 {ok} / 실패 {failed})\n\n"
        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n")
    git("commit", "-m", msg)
    r = git("push", check=False)
    if r.returncode:
        print(f"[push failed] {r.stderr.strip()[:200]}", flush=True)
    else:
        print(f"pushed: {n}곡 (정상 {ok} / 실패 {failed})", flush=True)


if __name__ == "__main__":
    main()
