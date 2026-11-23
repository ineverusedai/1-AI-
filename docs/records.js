/* 브라우저 안 기록 저장 + CSV 내려받기.
 * 정적 페이지는 results/ 폴더에 직접 쓸 수 없어서, 이 브라우저에 저장해 두고
 * 버튼으로 answers.csv / summary.csv 를 내려받는다 (Python 서버 버전과 같은 열 구성). */
(function () {
  const ANSWER_FIELDS = ["timestamp", "who", "mission", "mode", "attempt", "q_no",
    "submitted", "correct", "question_ms", "total_ms"];
  const SUMMARY_FIELDS = ["timestamp", "who", "mission", "mode", "attempt", "success",
    "answered", "correct", "max_streak", "total_ms",
    "first10_correct", "first10_ms", "correct_in_limit", "note"];
  const KEY = "hv24.records.v2";  // v2: 문제 세트 변경 (헷갈리는 글자 줄임)
  let mem = { answers: [], summary: [], state: {} };  // 저장소가 막혀 있어도 이번 화면에서는 동작

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) mem = Object.assign({ answers: [], summary: [], state: {} }, JSON.parse(raw));
    } catch (e) { /* 개인정보 보호 모드 등: 메모리에만 기록 */ }
    return mem;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch (e) { }
  }
  function nowIso() {
    const d = new Date(), pad = n => String(n).padStart(2, "0");
    const off = -d.getTimezoneOffset(), sign = off >= 0 ? "+" : "-";
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
      `${sign}${pad(Math.floor(Math.abs(off) / 60))}:${pad(Math.abs(off) % 60)}`;
  }
  function csv(fields, rows) {
    const esc = v => {
      const s = v === undefined || v === null ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    return "﻿" + [fields.join(","), ...rows.map(r => fields.map(f => esc(r[f])).join(","))].join("\r\n") + "\r\n";
  }
  function download(name, text) {
    const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  load();
  window.HV = window.HV || {};
  window.HV.records = {
    state(mission) { return mem.state[mission] || (mem.state[mission] = { next_q: 1, attempt: 0 }); },
    saveState() { save(); },
    logAnswer(row) { mem.answers.push(Object.assign({ timestamp: nowIso() }, row)); save(); },
    logSummary(row) { mem.summary.push(Object.assign({ timestamp: nowIso() }, row)); save(); },
    counts() { return { answers: mem.answers.length, summary: mem.summary.length }; },
    downloadAll() {
      download("answers.csv", csv(ANSWER_FIELDS, mem.answers));
      setTimeout(() => download("summary.csv", csv(SUMMARY_FIELDS, mem.summary)), 400);
    },
    clearAll() { mem = { answers: [], summary: [], state: {} }; save(); },
  };
})();
