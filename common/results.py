"""results/ 폴더 CSV 기록.

- results/answers.csv : 답 하나당 한 줄 (누가, 미션, 방식, 도전 번호, 문제 번호, 제출한 답, 정답 여부, 걸린 시간)
- results/summary.csv : 도전(또는 AI 실행) 하나당 한 줄
엑셀에서 한글이 깨지지 않게 UTF-8 BOM으로 만든다.
"""
import csv
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

ANSWER_FIELDS = ["timestamp", "who", "mission", "mode", "attempt", "q_no",
                 "submitted", "correct", "question_ms", "total_ms"]
SUMMARY_FIELDS = ["timestamp", "who", "mission", "mode", "attempt", "success",
                  "answered", "correct", "max_streak", "total_ms",
                  "first10_correct", "first10_ms", "correct_in_limit", "note"]

_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _append(name: str, fields: list[str], row: dict) -> None:
    path = RESULTS / name
    with _lock:
        RESULTS.mkdir(exist_ok=True)
        new = not path.exists() or path.stat().st_size == 0
        if new:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writerow({k: row.get(k, "") for k in fields})


def log_answer(row: dict) -> None:
    row.setdefault("timestamp", now_iso())
    _append("answers.csv", ANSWER_FIELDS, row)


def log_summary(row: dict) -> None:
    row.setdefault("timestamp", now_iso())
    _append("summary.csv", SUMMARY_FIELDS, row)
