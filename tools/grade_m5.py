"""미션 5 AI 플레이 기록(log.jsonl)을 다시 실행해 결과를 results/ 에 적는다.

실행: python -m tools.grade_m5 <log.jsonl> [--mode A] [--note "..."]
"""
import argparse
import json
import os
from pathlib import Path

from common import results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--mode", default="A")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    log_path = Path(a.log).resolve()
    os.chdir(log_path.parent)  # arc_play 는 작업 폴더의 log.jsonl 을 읽는다
    from tools import arc_play
    log = arc_play.load_log()
    st = arc_play.replay(log)
    t0 = log[0]["t"]
    acts = [e for e in log if e["kind"] == "act"]
    total_ms = int((log[-1]["t"] - t0) * 1000)
    lv = sum(g["levels"] for g in st["games"])
    allv = sum(g["win"] for g in st["games"])
    for i, g in enumerate(st["games"]):
        results.log_answer({"who": "claude", "mission": "m5", "mode": a.mode, "attempt": 1, "q_no": i + 1,
                            "submitted": f"{arc_play.GAMES[i][0]} {g['levels']}/{g['win']}단계 행동{g['count']}회",
                            "correct": int(g["state"] == "WIN"), "question_ms": "", "total_ms": total_ms})
    note = f"깬 단계 {lv}/{allv}; " + ", ".join(f"{arc_play.GAMES[i][0]} {g['levels']}/{g['win']} 행동{g['count']}" for i, g in enumerate(st["games"]))
    if arc_play.OFFICIAL:
        # 단계별 행동 수 (사람 기준과 비교) + 30분 시점에 깬 단계
        per = "; ".join(f"{arc_play.GAMES[i][0]} 단계별 행동 {g['per_level']} (사람 기준 {arc_play.BASE[arc_play.GAMES[i][0]][:len(g['per_level'])]})"
                        + (" 상한 초과로 끝" if arc_play.budget_out(i, g) else "") for i, g in enumerate(st["games"]))
        cut = t0 + arc_play.CFG.get("checkpoint_min", 30) * 60
        st30 = arc_play.replay([e for e in log if e["t"] <= cut])
        lv30 = sum(g["levels"] for g in st30["games"])
        note += f"; 공식 방식(단계별 행동 상한 = 사람 기준 × {arc_play.MULT}); {per}; 30분 시점 깬 단계 {lv30}/{allv}"
    summary = {"who": "claude", "mission": "m5", "mode": a.mode, "attempt": 1,
               "success": int(all(g["state"] == "WIN" for g in st["games"])), "answered": len(acts),
               "correct": sum(g["state"] == "WIN" for g in st["games"]), "max_streak": lv, "total_ms": total_ms,
               "first10_correct": "", "first10_ms": "", "correct_in_limit": lv, "note": (note + "; " + a.note).strip("; ")}
    results.log_summary(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
