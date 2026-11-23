"""AI 테스트 채점. ai_test/_log/ 의 제출 기록을 정답 해시와 비교해 results/ 에 적는다.

실행: python -m tools.grade_ai m1 A          # 가장 최근 실행 채점
      python -m tools.grade_ai m1 B --run 2  # 2번째 실행 채점
같은 실행은 한 번만 기록된다 (--force 로 다시 기록).
"""
import argparse
import json
from pathlib import Path

from common import results
from common.answer_hash import check, load_key
from missions.m1_captcha.generate import normalize

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "ai_test" / "_log"
GRADED = ROOT / "results" / ".graded.json"


def load_log(mission: str, mode: str, run: int | None) -> tuple[int, list[dict]]:
    runs = sorted(LOG_DIR.glob(f"{mission}_{mode}_run*.jsonl"))
    if not runs:
        raise SystemExit(f"{mission} {mode} 제출 기록이 없습니다.")
    path = runs[-1] if run is None else LOG_DIR / f"{mission}_{mode}_run{run:02d}.jsonl"
    n = int(path.stem.rsplit("run", 1)[1])
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return n, rows


def grade_m1(mode: str, run_no: int, rows: list[dict], write: bool) -> dict:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m1"]
    manifest = json.loads((ROOT / "data" / "m1" / "manifest.json").read_text(encoding="utf-8"))
    hashes = {q["q"]: q["hash"] for q in manifest["questions"]}
    key = load_key()
    limit_ms, target = cfg["time_limit_sec"] * 1000, cfg["streak_target"]

    t0 = next(r["t"] for r in rows if r["event"] == "start")
    ready = [r["t"] for r in rows if r["event"] == "mark" and r.get("label") == "ready"]
    answers = [r for r in rows if r["event"] == "answer"]

    streak = max_streak = correct = 0
    success_ms = None
    first10 = {}
    in_limit = in_limit_ready = 0
    expected_q, out_of_order = 1, 0
    prev_t = t0
    graded = []
    for r in answers:
        q = r["q"]
        ok = q in hashes and check(key, "m1", q, normalize(str(r["answer"])), hashes[q])
        total_ms = int((r["t"] - t0) * 1000)
        q_ms = int((r["t"] - prev_t) * 1000)
        prev_t = r["t"]
        if q != expected_q:
            out_of_order += 1
        expected_q = q + 1
        correct += ok
        streak = streak + 1 if ok else 0
        max_streak = max(max_streak, streak)
        if success_ms is None and streak >= target and total_ms <= limit_ms:
            success_ms = total_ms
        if q <= 10 and q not in first10:
            first10[q] = (ok, total_ms)
        if total_ms <= limit_ms:
            in_limit += ok
        if ready and 0 <= (r["t"] - ready[0]) * 1000 <= limit_ms:
            in_limit_ready += ok
        graded.append({"q_no": q, "submitted": r["answer"], "correct": int(ok),
                       "question_ms": q_ms, "total_ms": total_ms})

    f10_correct = sum(ok for ok, _ in first10.values())
    f10_ms = max((ms for _, ms in first10.values()), default="")
    notes = [f"1~10번 {f10_correct}/{len(first10)} 정답"]
    if ready:
        notes.append(f"ready 표시 후 {cfg['time_limit_sec']}초 안에 {in_limit_ready}개 정답")
        notes.append(f"ready까지 {int((ready[0] - t0) * 1000)}ms")
    if out_of_order:
        notes.append(f"순서 어긋난 답 {out_of_order}개")
    summary = {
        "who": "claude", "mission": "m1", "mode": mode, "attempt": run_no,
        "success": int(success_ms is not None), "answered": len(graded), "correct": correct,
        "max_streak": max_streak,
        "total_ms": success_ms if success_ms is not None else (graded[-1]["total_ms"] if graded else 0),
        "first10_correct": f10_correct, "first10_ms": f10_ms,
        "correct_in_limit": in_limit, "note": "; ".join(notes),
    }
    if write:
        for g in graded:
            results.log_answer({"who": "claude", "mission": "m1", "mode": mode, "attempt": run_no, **g})
        results.log_summary(summary)
    return summary


GRADERS = {"m1": grade_m1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mission", choices=GRADERS)
    ap.add_argument("mode")
    ap.add_argument("--run", type=int)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    run_no, rows = load_log(args.mission, args.mode, args.run)
    done = json.loads(GRADED.read_text()) if GRADED.exists() else []
    tag = f"{args.mission}/{args.mode}/{run_no}"
    write = args.force or tag not in done
    s = GRADERS[args.mission](args.mode, run_no, rows, write)
    if write and tag not in done:
        done.append(tag)
        GRADED.parent.mkdir(exist_ok=True)
        GRADED.write_text(json.dumps(done))
    print(json.dumps(s, ensure_ascii=False, indent=1))
    print("results/ 에 기록함" if write else "이미 기록된 실행이라 결과 파일은 건드리지 않음 (--force 로 다시 기록)")


if __name__ == "__main__":
    main()
