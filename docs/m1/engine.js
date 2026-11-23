/* 미션 1 웹 버전 채점·기록 (서버 없음). 채점은 브라우저 안에서 HMAC 해시 비교. */
(function () {
  const D = window.M1_DATA, R = HV.records, MISSION = "m1";
  const limitMs = D.time_limit_sec * 1000, target = D.streak_target, total = D.questions.length;
  const state = R.state(MISSION);
  const src = (q) => "images/" + D.questions[q - 1].file;
  let a = null;

  UI.config({ limitSec: D.time_limit_sec, streakTarget: target });

  UI.on("start", () => {
    if (a && !a.done) return;
    if (state.next_q > total) { UI.note("문제를 모두 풀었어요. Shift+R을 누르면 처음부터 시작해요"); return; }
    state.attempt += 1; R.saveState();
    a = { attempt: state.attempt, q: state.next_q, streak: 0, maxStreak: 0, answered: 0, correct: 0,
          first10: [], lastMs: 0, done: false };
    UI.setQuestion(src(a.q), a.q < total ? src(a.q + 1) : null);
    UI.beginRound(() => finish(false, limitMs, "timeout"));
  });

  UI.on("submit", (val) => {
    if (!a || a.done) return;
    const totalMs = Math.round(UI.elapsed());
    if (totalMs > limitMs) return finish(false, limitMs, "timeout");
    const qNo = a.q;
    const ok = HV.answerHash(D.key, MISSION, qNo, val.toUpperCase()) === D.questions[qNo - 1].hash;
    a.answered += 1; a.correct += ok ? 1 : 0;
    a.streak = ok ? a.streak + 1 : 0; a.maxStreak = Math.max(a.maxStreak, a.streak);
    if (a.first10.length < 10) a.first10.push([ok ? 1 : 0, totalMs]);
    R.logAnswer({ who: "human", mission: MISSION, mode: "human", attempt: a.attempt, q_no: qNo,
                  submitted: val, correct: ok ? 1 : 0, question_ms: totalMs - a.lastMs, total_ms: totalMs });
    a.lastMs = totalMs;
    state.next_q = qNo + 1; R.saveState();
    a.q = qNo + 1;
    UI.feedback(ok);
    UI.setStreak(a.streak);
    if (a.streak >= target) return finish(true, totalMs, "success");
    if (a.q > total) return finish(false, totalMs, "out_of_questions");
    UI.setQuestion(src(a.q), a.q < total ? src(a.q + 1) : null);
  });

  function finish(success, totalMs, reason) {
    if (!a || a.done) return;
    a.done = true;
    UI.stopClock(totalMs);
    const f10 = a.first10;
    R.logSummary({ who: "human", mission: MISSION, mode: "human", attempt: a.attempt,
      success: success ? 1 : 0, answered: a.answered, correct: a.correct, max_streak: a.maxStreak,
      total_ms: totalMs, first10_correct: f10.length === 10 ? f10.reduce((s, x) => s + x[0], 0) : "",
      first10_ms: f10.length === 10 ? f10[9][1] : "", correct_in_limit: a.correct,
      note: success ? "성공" : reason === "timeout" ? "시간 초과" : "문제 소진" });
    UI.showResult({ success, totalMs, maxStreak: a.maxStreak });
  }

  UI.on("reset", () => { state.next_q = 1; R.saveState(); UI.note("1번 문제부터 다시 시작해요"); });
  UI.on("download", () => { R.downloadAll(); UI.note("기록을 내려받았어요"); });
})();
