/* 미션 4 웹 버전 채점·기록 (서버 없음). 고른 선택지 글자를 HMAC 해시로 비교.
 * 규칙: 제한 시간 안에 6문제 모두 정답. 하나라도 틀리거나 시간이 다 되면 실패.
 * 다시 도전하면 다음 번호 문제부터 (문제가 모자라면 1번부터). Shift+R = 1번부터. */
(function () {
  const D = window.M4_DATA, R = HV.records, MISSION = "m4";
  const per = D.questions_per_round, total = D.questions.length, limitMs = D.time_limit_sec * 1000;
  const params = new URLSearchParams(location.search);
  const WHO = params.get("who") === "claude" ? "claude" : "human";
  const MODE = WHO === "claude" ? (["A", "B"].includes(params.get("mode")) ? params.get("mode") : "B") : "human";
  const state = R.state(WHO === "human" ? MISSION : `${MISSION}:${WHO}:${MODE}`);
  const src = (q) => "videos/" + D.questions[q - 1].file;
  const show = (q, last) => UI.setQuestion(src(q), q < last ? src(q + 1) : null, D.questions[q - 1].options);
  let a = null;

  UI.config({ limitSec: D.time_limit_sec, streakTarget: per });

  // 한 판의 영상 6개를 먼저 다 받은 뒤에 시작 (받는 시간이 제한 시간에 들어가지 않게)
  const roundUrls = () => { const s0 = state.next_q + per - 1 > total ? 1 : state.next_q; return Array.from({ length: per }, (_, i) => src(s0 + i)); };
  let loading = false;
  const btns = () => [document.getElementById("startBtn"), document.getElementById("retryBtn")];
  UI.prefetch(roundUrls());  // 페이지를 열자마자 다음 판을 미리 받기 시작
  UI.on("start", () => {
    if ((a && !a.done) || loading) return;
    if (state.next_q + per - 1 > total) state.next_q = 1;
    loading = true;
    const labels = btns().map((b) => b.textContent);
    UI.prefetch(roundUrls(), (n, m) => btns().forEach((b) => { b.textContent = `영상 불러오는 중 ${n}/${m}`; })).then(() => {
      btns().forEach((b, i) => { b.textContent = labels[i]; });
      loading = false;
      state.attempt += 1; R.saveState();
      a = { attempt: state.attempt, q: state.next_q, last: state.next_q + per - 1, count: 0, correct: 0, lastMs: 0, done: false };
      show(a.q, a.last);
      UI.beginRound(() => finish(false, limitMs, "timeout"));
    });
  });

  UI.on("submit", (val) => {
    if (!a || a.done) return;
    const totalMs = Math.round(UI.elapsed());
    if (totalMs > limitMs) return finish(false, limitMs, "timeout");
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
    show(a.q, a.last);
  });

  function finish(success, totalMs, reason) {
    if (!a || a.done) return;
    a.done = true;
    UI.stopClock(totalMs);
    R.logSummary({ who: WHO, mission: MISSION, mode: MODE, attempt: a.attempt,
      success: success ? 1 : 0, answered: a.count, correct: a.correct, max_streak: a.correct,
      total_ms: totalMs, first10_correct: "", first10_ms: "", correct_in_limit: a.correct,
      note: success ? "성공" : reason === "timeout" ? "시간 초과" : `${a.count}번째 문제에서 틀림` });
    UI.showResult({ success, totalMs, maxStreak: a.correct });
    UI.prefetch(roundUrls());  // 다음 판 미리 받기
  }

  UI.on("reset", () => { state.next_q = 1; R.saveState(); UI.note("1번 문제부터 다시 시작해요"); });
  UI.on("download", () => { R.downloadAll(); UI.note("기록을 내려받았어요"); });
})();
