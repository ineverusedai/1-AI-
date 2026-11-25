/* 미션 5: ARC-AGI-3 (브라우저 버전, 설치 없음).
 *
 * 공식 ARC-AGI-3 게임 소스(arcprize.org 에서 공식 toolkit 으로 받은 것, MIT)와 공식 엔진 arcengine(MIT)을
 * 브라우저 안의 파이썬(Pyodide)으로 그대로 돌린다. 게임 규칙은 한 글자도 바꾸지 않았다.
 *
 * 조작 (ARC-AGI-3 행동 번호)
 *   W / ↑ = ACTION1, S / ↓ = ACTION2, A / ← = ACTION3, D / → = ACTION4, Space = ACTION5,
 *   화면 클릭 = ACTION6 (칸 좌표), Z = ACTION7 (되돌리기), R = RESET (지금 단계 다시)
 *   1 / 2 / 3 또는 Tab = 게임 바꾸기
 * 규칙: 30분 안에 게임 3개를 모두 끝까지 깨면 성공. 깬 단계 수와 행동 수를 기록.
 * 숨은 단축키 (시작·결과 화면): Shift+R 기록 초기화 없이 다시, Shift+D 기록 CSV 내려받기
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const R = HV.records, MISSION = "m5";
  const params = new URLSearchParams(location.search);
  const WHO = params.get("who") === "claude" ? "claude" : "human";
  const MODE = WHO === "claude" ? (params.get("mode") || "A") : "human";
  // ?rule=official : ARC-AGI-3 공식 방식 (시간 제한 없음, 경과 시간 표시). AI 공식 플레이 리플레이용. 기본은 사람용 30분 타이머
  const OFFICIAL = params.get("rule") === "official";
  const LIMIT_MS = OFFICIAL ? Infinity : 30 * 60 * 1000;
  const GAMES = [{ id: "ls20", cls: "Ls20" }, { id: "ft09", cls: "Ft09" }, { id: "vc33", cls: "Vc33" }];
  const COLORS = ["#FFFFFF", "#CCCCCC", "#999999", "#666666", "#333333", "#000000", "#E53AA3", "#FF7BCC",
                  "#F93C31", "#1E93FF", "#88D8F1", "#FFDC00", "#FF851B", "#921231", "#4FCC30", "#A356D6"];  // toolkit COLOR_MAP
  const RGB = COLORS.map((h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)));
  const KEYMAP = { w: 1, arrowup: 1, s: 2, arrowdown: 2, a: 3, arrowleft: 3, d: 4, arrowright: 4, " ": 5, z: 7, r: 0 };

  let W = null, cur = 0, busy = false, run = null, t0 = 0, raf = 0, clockOn = false;
  const ctx = $("arc").getContext("2d");
  const img = ctx.createImageData(64, 64);

  /* ---------- 파이썬 엔진 부팅 ---------- */
  async function boot() {
    const py = await loadPyodide({ indexURL: "pyodide/" });
    await py.loadPackage(["numpy", "pydantic"]);
    py.FS.mkdirTree("/arc/arcengine");
    for (const f of ["__init__", "base_game", "camera", "enums", "interfaces", "level", "sprites"]) {
      py.FS.writeFile(`/arc/arcengine/${f}.py`, await (await fetch(`py/arcengine/${f}.py`)).text());
    }
    py.FS.writeFile("/arc/arcweb.py", await (await fetch("py/arcweb.py")).text());
    py.runPython("import sys; sys.path.insert(0, '/arc')");
    W = py.pyimport("arcweb");
    for (const g of GAMES) {
      g.meta = await (await fetch(`games/${g.id}.json`)).json();
      g.src = await (await fetch(`games/${g.id}.py`)).text();
    }
  }

  function step(g, action, x = -1, y = -1) {
    const r = W.step(g.id, action, x, y);
    const [metaJson, bytes] = r.toJs();
    r.destroy();
    const m = JSON.parse(metaJson);
    const frames = [];
    for (let k = 0; k < m.n; k++) frames.push(bytes.subarray(k * m.h * m.w, (k + 1) * m.h * m.w));
    return { ...m, frames };
  }

  /* ---------- 화면 ---------- */
  function draw(frame) {
    for (let i = 0; i < 4096; i++) {
      const c = RGB[frame[i]] || RGB[5];
      img.data[i * 4] = c[0]; img.data[i * 4 + 1] = c[1]; img.data[i * 4 + 2] = c[2]; img.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }
  function play(frames, fps) {  // 여러 프레임(애니메이션)이면 게임의 기본 fps 로 보여 준다
    return new Promise((done) => {
      if (!frames.length) return done();
      let k = 0;
      const gap = 1000 / Math.max(1, fps || 10);
      const next = () => {
        draw(frames[k]); k += 1;
        if (k < frames.length) setTimeout(next, gap); else done();
      };
      next();
    });
  }
  function totals() {
    const lv = run.games.reduce((s, g) => s + g.levels, 0);
    const all = run.games.reduce((s, g) => s + g.win, 0);
    return { lv, all };
  }
  function renderHud() {
    const { lv, all } = totals();
    $("lvNum").textContent = lv;
    $("lvTotal").textContent = all;
    $("gtabs").innerHTML = run.games.map((g, i) =>
      `<button class="gtab ${i === cur ? "on" : ""} ${g.state === "WIN" ? "won" : ""}" data-i="${i}">` +
      `<b>${i + 1}</b><span>${GAMES[i].id.toUpperCase()}</span><em>${g.state === "WIN" ? "✓" : `${g.levels}/${g.win}`}</em></button>`).join("");
    $("gtabs").querySelectorAll(".gtab").forEach((b) => { b.onclick = () => select(+b.dataset.i); });
    const acts = run.games[cur].actions;
    const has = (n) => acts.includes(n);
    const key = (label, on) => `<span class="key ${on ? "" : "off"}">${label}</span>`;
    $("keys").innerHTML =
      `<div class="krow">${key("↑", has(1))}</div><div class="krow">${key("←", has(3))}${key("↓", has(2))}${key("→", has(4))}</div>` +
      `<div class="krow">${key("Space", has(5))}${key("클릭", has(6))}${key("Z 되돌리기", has(7))}</div>` +
      `<div class="krow">${key("R 다시", true)}</div>`;
    const g = run.games[cur];
    const over = $("arcOver");
    over.hidden = g.state !== "GAME_OVER" && g.state !== "WIN";
    over.innerHTML = g.state === "WIN" ? "<b>✓</b><span>이 게임 완료</span>" : "<b>!</b><span>R을 눌러 다시</span>";
    over.className = "arcover " + (g.state === "WIN" ? "won" : "lost");
  }
  function select(i) {
    if (!run || run.done || busy) return;
    cur = i;
    draw(run.games[i].last);
    renderHud();
  }

  /* ---------- 행동 ---------- */
  async function act(action, x = -1, y = -1) {
    if (!run || run.done || busy) return;
    const g = run.games[cur];
    if (action !== 0 && !g.actions.includes(action)) return;
    if (g.state === "WIN") return;
    if (g.state === "GAME_OVER" && action !== 0) return;
    busy = true;
    const before = g.levels;
    const r = step(GAMES[cur], action, x, y);
    g.count += 1;
    run.log.push({ t: Math.round(elapsed()), game: GAMES[cur].id, action, x, y, levels: r.levels, state: r.state });
    g.levels = r.levels; g.win = r.win; g.state = r.state; g.actions = r.actions;
    if (r.frames.length) g.last = r.frames[r.frames.length - 1];
    await play(r.frames, GAMES[cur].meta.default_fps);
    busy = false;
    renderHud();
    if (g.levels > before) { feedback(true); note(`${GAMES[cur].id.toUpperCase()} ${g.levels}단계 통과`); }
    if (r.state === "GAME_OVER") feedback(false);
    if (r.state === "WIN") {
      if (run.games.every((x) => x.state === "WIN")) return finish(true);
      const nxt = run.games.findIndex((x) => x.state !== "WIN");
      setTimeout(() => select(nxt), 900);
    }
  }

  /* ---------- 시간 ---------- */
  const elapsed = () => performance.now() - t0;
  function drawTimer(ms) {
    if (OFFICIAL) {  // 경과 시간 (시:분:초)
      const s = Math.floor(ms / 1000), h = Math.floor(s / 3600);
      $("timer").textContent = (h ? `${h}:` : "") + `${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
      return;
    }
    const left = Math.max(0, LIMIT_MS - ms);
    const s = Math.ceil(left / 1000);
    const el = $("timer");  // 남은 시간
    el.textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    el.classList.toggle("low", left <= 5 * 60000 && left > 60000);
    el.classList.toggle("crit", left <= 60000);
  }
  function startClock() {
    t0 = performance.now(); clockOn = true;
    const loop = () => {
      if (!clockOn) return;
      const ms = elapsed();
      if (ms >= LIMIT_MS) { drawTimer(LIMIT_MS); return finish(false, LIMIT_MS); }
      drawTimer(ms);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
  }

  /* ---------- 시작·끝 ---------- */
  function start() {
    if (!W || (run && !run.done)) return;
    const state = R.state(WHO === "human" ? MISSION : `${MISSION}:${WHO}:${MODE}`);
    state.attempt += 1; R.saveState();
    run = { attempt: state.attempt, done: false, log: [], games: [] };
    for (const g of GAMES) {
      W.load(g.id, g.cls, g.src);  // 새로 만들어서 처음부터
      const r = step(g, 0);
      run.games.push({ levels: r.levels, win: r.win, state: r.state, actions: r.actions, count: 0, last: r.frames[r.frames.length - 1] });
    }
    cur = 0;
    hide("startScreen"); hide("resultScreen");
    draw(run.games[0].last);
    renderHud();
    startClock();
  }
  function finish(success, ms) {
    if (!run || run.done) return;
    run.done = true; clockOn = false; cancelAnimationFrame(raf);
    const totalMs = Math.round(ms != null ? ms : elapsed());
    drawTimer(totalMs);
    const { lv, all } = totals();
    run.games.forEach((g, i) => R.logAnswer({ who: WHO, mission: MISSION, mode: MODE, attempt: run.attempt, q_no: i + 1,
      submitted: `${GAMES[i].id} ${g.levels}/${g.win}단계 행동${g.count}회`, correct: g.state === "WIN" ? 1 : 0,
      question_ms: "", total_ms: totalMs }));
    R.logSummary({ who: WHO, mission: MISSION, mode: MODE, attempt: run.attempt, success: success ? 1 : 0,
      answered: run.games.reduce((s, g) => s + g.count, 0), correct: run.games.filter((g) => g.state === "WIN").length,
      max_streak: lv, total_ms: totalMs, first10_correct: "", first10_ms: "", correct_in_limit: lv,
      note: `깬 단계 ${lv}/${all}; ` + run.games.map((g, i) => `${GAMES[i].id} ${g.levels}/${g.win} 행동${g.count}`).join(", ") });
    window.M5_LAST_LOG = run.log;
    try { localStorage.setItem("hv24.m5.lastlog", JSON.stringify(run.log)); } catch (e) { }
    setTimeout(() => {
      const icon = $("resultIcon");
      icon.setAttribute("class", "result-icon" + (success ? "" : " bad"));
      icon.innerHTML = `<circle class="ring" cx="90" cy="90" r="86"/><g class="core"><circle class="bg" cx="90" cy="90" r="86"/>` +
        `<path d="${success ? "M52 92 L79 119 L130 64" : "M64 64 L116 116 M116 64 L64 116"}"/></g>`;
      $("resultTitle").innerHTML = success ? "인간 인증<br><em style=\"color:var(--green)\">성공</em>" : "인간 인증<br><em style=\"color:var(--red)\">실패</em>";
      const m = Math.floor(totalMs / 60000), s = Math.round((totalMs % 60000) / 1000);
      $("rTime").textContent = `${m}분 ${s}초`;
      $("rLevels").textContent = `${lv} / ${all}`;
      show("resultScreen");
      if (success) confetti();
    }, success ? 900 : 400);
  }

  /* ---------- 효과 (다른 미션과 같은 디자인) ---------- */
  const CHECK = "M50 86 L74 110 L120 60", CROSS = "M60 60 L108 108 M108 60 L60 108";
  function feedback(ok) {
    const fx = $("fx");
    fx.className = "fx " + (ok ? "ok" : "bad");
    fx.innerHTML = `<div class="burst"><svg viewBox="0 0 168 168"><circle class="ring" cx="84" cy="84" r="80"/>` +
      `<g class="core"><circle class="bg" cx="84" cy="84" r="80"/><path d="${ok ? CHECK : CROSS}"/></g></svg></div>`;
    fx.querySelector(".burst").animate([
      { opacity: 0, transform: "scale(.5)" }, { opacity: 1, transform: "scale(1.08)", offset: .22 },
      { opacity: 1, transform: "scale(1)", offset: .38 }, { opacity: 1, transform: "scale(1)", offset: .74 },
      { opacity: 0, transform: "scale(.94)" }], { duration: ok ? 900 : 1000, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" });
    fx.querySelector("path").animate([{ strokeDashoffset: 120 }, { strokeDashoffset: 0 }], { duration: 260, delay: 80, easing: "ease-out", fill: "forwards" });
    fx.querySelector(".ring").animate([{ transform: "scale(1)", opacity: .9 }, { transform: "scale(1.9)", opacity: 0 }],
      { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" });
    const v = $("vignette");
    v.className = "vignette " + (ok ? "ok" : "");
    v.animate([{ opacity: 0 }, { opacity: 1, offset: .2 }, { opacity: 0 }], { duration: ok ? 520 : 850, easing: "ease-out" });
  }
  function confetti() {
    const colors = ["#3182f6", "#2bd47d", "#ffffff", "#ffa41b", "#ff6b9a", "#a78bfa"];
    for (let i = 0; i < 90; i++) {
      const c = document.createElement("i");
      c.className = "confetti";
      c.style.left = Math.random() * 100 + "vw";
      c.style.background = colors[i % colors.length];
      document.body.appendChild(c);
      const drift = (Math.random() - .5) * 240, rot = (Math.random() - .5) * 1080;
      c.animate([{ transform: "translate(0,0) rotate(0deg)", opacity: 1 }, { transform: `translate(${drift}px, 105vh) rotate(${rot}deg)`, opacity: .9 }],
        { duration: 2200 + Math.random() * 1400, delay: Math.random() * 350, easing: "cubic-bezier(.25,.5,.4,1)", fill: "forwards" }).onfinish = () => c.remove();
    }
  }
  function show(id) { const el = $(id); el.hidden = false; el.classList.remove("enter"); void el.offsetWidth; el.classList.add("enter"); }
  function hide(id) { $(id).hidden = true; }
  function note(text) {
    const n = $("note");
    n.textContent = text;
    n.animate([{ opacity: 0, transform: "translate(-50%, 10px)" }, { opacity: 1, transform: "translate(-50%, 0)", offset: .15 },
               { opacity: 1, transform: "translate(-50%, 0)", offset: .8 }, { opacity: 0, transform: "translate(-50%, 0)" }],
              { duration: 1800, easing: "ease-out", fill: "forwards" });
  }
  const screenOpen = () => !$("startScreen").hidden || !$("resultScreen").hidden;

  /* ---------- 입력 ---------- */
  document.addEventListener("keydown", (e) => {
    if (screenOpen()) {
      if (e.key === "Enter" && W) { e.preventDefault(); start(); }
      else if (e.shiftKey && (e.key === "D" || e.key === "d")) { e.preventDefault(); R.downloadAll(); note("기록을 내려받았어요"); }
      return;
    }
    const k = e.key.toLowerCase();
    if (["1", "2", "3"].includes(k)) { e.preventDefault(); return select(+k - 1); }
    if (k === "tab") { e.preventDefault(); return select((cur + 1) % GAMES.length); }
    if (k in KEYMAP && !e.ctrlKey && !e.metaKey) { e.preventDefault(); act(KEYMAP[k]); }
  });
  $("arc").addEventListener("click", (e) => {
    const b = $("arc").getBoundingClientRect();
    const x = Math.floor((e.clientX - b.left) / b.width * 64), y = Math.floor((e.clientY - b.top) / b.height * 64);
    if (x >= 0 && x < 64 && y >= 0 && y < 64) act(6, x, y);
  });
  $("startBtn").onclick = start;
  $("retryBtn").onclick = start;

  // 녹화·AI 플레이용 (화면과 같은 입력 경로를 쓴다)
  if (OFFICIAL) document.addEventListener("DOMContentLoaded", () => { const l = $("timer").previousElementSibling; if (l) l.textContent = "경과 시간"; });
  window.M5 = { ready: () => !!W, busy: () => busy, running: () => !!run && !run.done,
                status: () => run && { cur, games: run.games.map((g, i) => ({ id: GAMES[i].id, levels: g.levels, win: g.win, state: g.state, actions: g.actions, count: g.count })) } };

  boot().then(() => { $("startBtn").disabled = false; $("startBtn").textContent = "시작하기"; })
        .catch((e) => { $("startBtn").textContent = "불러오지 못했어요"; console.error(e); });
})();
