"""미션 1 게임 로직 (서버 쪽). 채점은 해시 비교로만 한다.

규칙: 제한 시간 안에 연속 정답 N개. 틀리면 연속 카운트 0.
다시 도전하면 이미 본 문제는 건너뛰고 다음 번호부터 이어서 낸다 (외워서 푸는 것 방지).
"""
import json
import threading
import time
import uuid
from pathlib import Path

from common import results
from common.answer_hash import check, load_key

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "m1"
STATE = ROOT / "results" / ".state_m1.json"
MISSION = "m1"


class CaptchaGame:
    def __init__(self):
        self.cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m1"]
        self.manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
        self.qs = {q["q"]: q for q in self.manifest["questions"]}
        self.key = load_key()
        self.lock = threading.Lock()
        self.attempts: dict[str, dict] = {}
        self.state = self._load_state()

    # ---------- 진행 상태 (다음 문제 번호, 도전 횟수) ----------
    def _load_state(self) -> dict:
        if STATE.exists():
            return json.loads(STATE.read_text())
        return {"next_q": 1, "attempt": 0}

    def _save_state(self) -> None:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(self.state))

    def info(self) -> dict:
        return {
            "title": self.cfg["title"],
            "time_limit_sec": self.cfg["time_limit_sec"],
            "streak_target": self.cfg["streak_target"],
            "next_q": self.state["next_q"],
            "next_attempt": self.state["attempt"] + 1,
            "pool_size": len(self.qs),
            "answer_rule": self.manifest["answer_rule"],
        }

    def reset(self) -> dict:
        with self.lock:
            self.state["next_q"] = 1
            self._save_state()
        return self.info()

    def _question(self, q_no: int) -> dict:
        return {"q_no": q_no, "image": f"/data/m1/images/{self.qs[q_no]['file']}"}

    # ---------- 도전 ----------
    def start(self) -> dict:
        with self.lock:
            if self.state["next_q"] > len(self.qs):
                return {"error": "문제를 모두 사용했습니다. '처음 문제부터'를 누르세요."}
            self.state["attempt"] += 1
            self._save_state()
            aid = uuid.uuid4().hex
            now = time.monotonic()
            self.attempts[aid] = {
                "id": aid, "attempt": self.state["attempt"], "t0": now, "t_last": now,
                "q_no": self.state["next_q"], "streak": 0, "max_streak": 0,
                "answered": 0, "correct": 0, "first10": [], "done": False,
            }
            return {"attempt_id": aid, "attempt": self.state["attempt"],
                    **self.info(), "question": self._question(self.state["next_q"])}

    def _finish(self, a: dict, success: bool, total_ms: int, note: str) -> None:
        a["done"] = True
        f10 = a["first10"]
        results.log_summary({
            "who": "human", "mission": MISSION, "mode": "human", "attempt": a["attempt"],
            "success": int(success), "answered": a["answered"], "correct": a["correct"],
            "max_streak": a["max_streak"], "total_ms": total_ms,
            "first10_correct": sum(c for c, _ in f10) if len(f10) == 10 else "",
            "first10_ms": f10[-1][1] if len(f10) == 10 else "",
            "correct_in_limit": a["correct"], "note": note,
        })

    def _summary(self, a: dict, success: bool, total_ms: int, reason: str) -> dict:
        return {"done": True, "success": success, "reason": reason, "total_ms": total_ms,
                "answered": a["answered"], "correct": a["correct"], "max_streak": a["max_streak"],
                "streak": a["streak"], "attempt": a["attempt"]}

    def answer(self, aid: str, submitted: str) -> dict:
        with self.lock:
            a = self.attempts.get(aid)
            if not a or a["done"]:
                return {"error": "끝난 도전입니다."}
            now = time.monotonic()
            total_ms = int((now - a["t0"]) * 1000)
            limit_ms = self.cfg["time_limit_sec"] * 1000
            if total_ms > limit_ms:
                self._finish(a, False, limit_ms, "시간 초과")
                return self._summary(a, False, limit_ms, "timeout")

            submitted = submitted.strip()
            q_no = a["q_no"]
            ok = check(self.key, MISSION, q_no, submitted, self.qs[q_no]["hash"])
            q_ms = int((now - a["t_last"]) * 1000)
            a["t_last"] = now
            a["answered"] += 1
            a["correct"] += ok
            a["streak"] = a["streak"] + 1 if ok else 0
            a["max_streak"] = max(a["max_streak"], a["streak"])
            if len(a["first10"]) < 10:
                a["first10"].append((int(ok), total_ms))
            results.log_answer({
                "who": "human", "mission": MISSION, "mode": "human", "attempt": a["attempt"],
                "q_no": q_no, "submitted": submitted, "correct": int(ok),
                "question_ms": q_ms, "total_ms": total_ms,
            })

            self.state["next_q"] = q_no + 1
            self._save_state()
            a["q_no"] = q_no + 1

            if a["streak"] >= self.cfg["streak_target"]:
                self._finish(a, True, total_ms, "성공")
                return {"correct": ok, **self._summary(a, True, total_ms, "success")}
            if a["q_no"] > len(self.qs):
                self._finish(a, False, total_ms, "문제 소진")
                return {"correct": ok, **self._summary(a, False, total_ms, "out_of_questions")}
            return {"correct": ok, "done": False, "streak": a["streak"], "answered": a["answered"],
                    "correct_count": a["correct"], "question": self._question(a["q_no"])}

    def end(self, aid: str) -> dict:
        """브라우저 타이머가 0이 됐을 때 호출."""
        with self.lock:
            a = self.attempts.get(aid)
            if not a:
                return {"error": "없는 도전입니다."}
            limit_ms = self.cfg["time_limit_sec"] * 1000
            if not a["done"]:
                self._finish(a, False, limit_ms, "시간 초과")
            return self._summary(a, False, limit_ms, "timeout")
