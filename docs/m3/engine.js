/* 미션 3 웹 버전 채점·기록 (서버 없음). 고른 번호(1~4)를 HMAC 해시로 비교.
 * 규칙: 한 판에 5문제, 하나라도 틀리면 바로 실패. 시간 제한 없음 (걸린 시간 기록).
 * 다시 도전하면 다음 번호 문제부터 (문제 20개, 다 쓰면 1번부터). Shift+R = 1번부터. */
(function () {
  const D = window.M3_DATA, R = HV.records, MISSION = "m3";
  const per = D.questions_per_round, total = D.questions.length;
  const params = new URLSearchParams(location.search);
  const WHO = params.get("who") === "claude" ? "claude" : "human";
  const MODE = WHO === "claude" ? (["A", "B"].includes(params.get("mode")) ? params.get("mode") : "B") : "human";
  const state = R.state(WHO === "human" ? MISSION : `${MISSION}:${WHO}:${MODE}`);
  const qdata = (q) => {
    const d = "audio/" + D.questions[q - 1].dir + "/";
    return { ref: d + "ref.wav", opts: [1, 2, 3, 4].map((n) => d + `opt${n}.wav`) };
  };
  let a = null;

  UI.config({ limitSec: null, streakTarget: per });

  UI.on("start", () => {
    if (a && !a.done) return;
    if (state.next_q + per - 1 > total) state.next_q = 1;  // 남은 문제가 한 판보다 적으면 처음부터
    state.attempt += 1; R.saveState();
    a = { attempt: state.attempt, q: state.next_q, count: 0, correct: 0, lastMs: 0, done: false };
    UI.setQuestion(qdata(a.q));
    UI.beginRound(null);
  });

  UI.on("submit", (val) => {
    if (!a || a.done) return;
    const totalMs = Math.round(UI.elapsed());
    const qNo = a.q;
    const ok = HV.answerHash(D.key, MISSION, qNo, val) === D.questions[qNo - 1].hash;
    a.count += 1; a.correct += ok ? 1 : 0;
    R.logAnswer({ who: WHO, mission: MISSION, mode: MODE, attempt: a.attempt, q_no: qNo,
                  submitted: val, correct: ok ? 1 : 0, question_ms: totalMs - a.lastMs, total_ms: totalMs });
    a.lastMs = totalMs;
    state.next_q = qNo + 1; R.saveState();
    UI.feedback(ok);
    UI.setStreak(a.correct);
    if (!ok) return finish(false, totalMs, "wrong");
    if (a.count >= per) return finish(true, totalMs, "success");
    a.q = qNo + 1;
    UI.setQuestion(qdata(a.q));
  });

  function finish(success, totalMs, reason) {
    if (!a || a.done) return;
    a.done = true;
    UI.stopClock(totalMs);
    R.logSummary({ who: WHO, mission: MISSION, mode: MODE, attempt: a.attempt,
      success: success ? 1 : 0, answered: a.count, correct: a.correct, max_streak: a.correct,
      total_ms: totalMs, first10_correct: "", first10_ms: "", correct_in_limit: a.correct,
      note: success ? "성공" : `${a.count}번째 문제에서 틀림` });
    UI.showResult({ success, totalMs, maxStreak: a.correct });
  }

  UI.on("reset", () => { state.next_q = 1; R.saveState(); UI.note("1번 문제부터 다시 시작해요"); });
  UI.on("download", () => { R.downloadAll(); UI.note("기록을 내려받았어요"); });
})();
