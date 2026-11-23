"""AI 테스트 답안 제출기. 채점은 하지 않는다 — 답과 시각만 기록한다.

사용법 (ai_test 폴더 안에서):
  python submit.py <미션> <방식> start               # 시작 시각 기록 (새 실행 번호가 매겨짐)
  python submit.py <미션> <방식> answer <번호> <답>   # 답 하나 기록
  python submit.py <미션> <방식> mark <이름>          # 표시 남기기 (예: mark ready = 프로그램 준비 끝)
  python submit.py <미션> <방식> end                 # 끝

예: python submit.py m1 A start
    python submit.py m1 A answer 1 "AB0lI"

프로그램 안에서 쓸 때:
  from submit import record
  record("m1", "B", "answer", q=1, answer="AB0lI")
"""
import json
import sys
import time
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "_log"


def _current(mission: str, mode: str) -> Path | None:
    runs = sorted(LOG_DIR.glob(f"{mission}_{mode}_run*.jsonl"))
    return runs[-1] if runs else None


def record(mission: str, mode: str, event: str, **data) -> dict:
    LOG_DIR.mkdir(exist_ok=True)
    if event == "start":
        n = len(list(LOG_DIR.glob(f"{mission}_{mode}_run*.jsonl"))) + 1
        path = LOG_DIR / f"{mission}_{mode}_run{n:02d}.jsonl"
    else:
        path = _current(mission, mode)
        if path is None:
            raise SystemExit("먼저 start 를 실행하세요.")
    row = {"t": time.time(), "event": event, **data}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        raise SystemExit(__doc__)
    mission, mode, event = argv[0], argv[1], argv[2]
    if event == "answer":
        if len(argv) != 5:
            raise SystemExit("answer <번호> <답> 형식으로 입력하세요.")
        row = record(mission, mode, "answer", q=int(argv[3]), answer=argv[4])
    elif event == "mark":
        row = record(mission, mode, "mark", label=" ".join(argv[3:]) or "mark")
    elif event in ("start", "end"):
        row = record(mission, mode, event)
    else:
        raise SystemExit(__doc__)
    print("기록됨:", json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
