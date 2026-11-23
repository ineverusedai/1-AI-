/* 미션 1 Python 서버 버전 채점·기록. 채점과 시간 판정은 서버(run.py)가 하고 results/ 에 바로 저장한다. */
(function () {
  const api = (action, body = {}) =>
    fetch(`/api/m1/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json());
  let attemptId = null, busy = false, active = false;

  fetch("/api/m1/info").then((r) => r.json()).then((info) => UI.config({ limitSec: info.time_limit_sec, streakTarget: info.streak_target }));

  UI.on("start", async () => {
    if (busy || active) return;
    busy = true;
    const r = await api("start");
    busy = false;
    if (r.error) { UI.note(r.error); return; }
    attemptId = r.attempt_id;
    active = true;
    UI.setQuestion(r.question.image);
    UI.beginRound(async () => {
      if (!active) return;
      active = false;
      const s = await api("end", { attempt_id: attemptId });
      UI.showResult({ success: false, totalMs: s.total_ms, maxStreak: s.max_streak });
    });
  });

  UI.on("submit", async (val) => {
    if (!active || busy) return;
    busy = true;
    const r = await api("answer", { attempt_id: attemptId, answer: val });
    busy = false;
    if (r.error) return;
    if ("correct" in r) UI.feedback(r.correct);
    if (r.streak !== undefined) UI.setStreak(r.streak);
    if (r.done) {
      active = false;
      UI.stopClock(r.total_ms);
      UI.showResult({ success: r.success, totalMs: r.total_ms, maxStreak: r.max_streak });
      return;
    }
    UI.setQuestion(r.question.image);
  });

  UI.on("reset", async () => { await api("reset"); UI.note("1번 문제부터 다시 시작해요"); });
  UI.on("download", () => UI.note("기록은 results/ 폴더에 자동으로 저장돼요"));
})();
