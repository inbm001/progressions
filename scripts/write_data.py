"""done/ 의 결과를 data/ 로 모은다. 수집을 돌리지 않고 집계만 다시 한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import write_outputs, DATA
import json

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

write_outputs()
idx = json.loads((DATA / "index.json").read_text(encoding="utf-8"))
print(f"전체 {idx['count']} / 정상 {idx['ok']} / 실패 {idx['failed']}")
