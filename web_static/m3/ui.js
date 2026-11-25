/* 미션 3 화면과 효과 (원본 듣기 → 사인파 음성 4개 중 고르기). 채점·기록은 engine.js 가 맡는다.
 * 재생 순서 (IllusionAudio 방식): 문제가 나오면 깨끗한 원본 → 사인파 소리 1 → 2 → 3 → 4 가 자동으로 차례로 나온다.
 * 조작: 소리 1~4 클릭 또는 키보드 1~4 로 고르기(고르기만, 재생 안 함), 확인 버튼 또는 Enter. 다 나온 뒤 '다시 듣기'(Space)로 처음부터 다시.
 * 시간 제한 없음 (논문·사양 모두 통과/실패로 평가). 보조 기록으로 '고르는 시간'을 잰다:
 * 소리가 나오는 동안(차례 재생·다시 듣기, 사이 쉬는 시간 포함)은 멈추고, 소리가 없을 때만 올라간다.
 *
 * 숨은 단축키 (시작·결과 화면에서만)
 *   Shift + R : 1번 문제부터 다시
 *   Shift + D : 기록 CSV 내려받기 (웹 버전)
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const UI = {};
  const handlers = {};
  let limitMs = 60000, target = 10, t0 = 0, raf = 0, clockOn = false, lastSec = null, curStreak = 0;

  UI.on = (name, fn) => { handlers[name] = fn; };
  const emit = (name, ...args) => handlers[name] && handlers[name](...args);

  /* ---------- 설정 ---------- */
  UI.config = ({ limitSec, streakTarget }) => {
    limitMs = 0;
    target = streakTarget;
    $("target").textContent = target;
    $("startHead").innerHTML = `원본과 같은 문장을<br><em>${target}문제</em> 모두 맞히세요`;
    $("segs").innerHTML = "<i></i>".repeat(target);
    renderStreak(0, false);
    drawTimer(0);
  };

  /* ---------- 연속 정답 ---------- */
  function renderStreak(n, animate) {
    const prev = curStreak;
    curStreak = n;
    const b = $("streakNum");
    b.textContent = n;
    const segs = $("segs").children;
    for (let i = 0; i < segs.length; i++) {
      segs[i].classList.toggle("on", i < n);
      segs[i].classList.remove("pop");
    }
    if (!animate) return;
    b.classList.remove("up", "zero");
    void b.offsetWidth;
    if (n > prev) {
      b.classList.add("up");
      const seg = segs[n - 1];
      if (seg) { void seg.offsetWidth; seg.classList.add("pop"); }
    } else if (n < prev) {
      b.classList.add("zero");
      const s = $("segs");
      s.classList.add("reset");
      setTimeout(() => s.classList.remove("reset"), 380);
    }
    clearTimeout(b._t);
    b._t = setTimeout(() => b.classList.remove("up", "zero"), 650);
  }
  UI.setStreak = (n) => renderStreak(n, true);

  /* ---------- 시간 ---------- */
  let think = 0, lastTick = 0, listening = false;
  function drawTimer(ms) {
    $("timer").firstChild.nodeValue = (Math.max(0, ms) / 1000).toFixed(1);  // 고르는 시간 (소리 나오는 동안 멈춤)
    $("timer").classList.toggle("paused", listening);
  }
  function tick() {  // 소리가 없을 때만 고르는 시간을 더한다
    const now = performance.now();
    if (clockOn && !listening) think += now - lastTick;
    lastTick = now;
  }
  UI.elapsed = () => performance.now() - t0;      // 전체 경과 (소리 포함)
  UI.thinkMs = () => { tick(); return think; };   // 고르는 시간
  function setListening(v) { tick(); listening = v; drawTimer(think); }
  function startClock(onTimeout) {
    t0 = lastTick = performance.now();
    think = 0;
    clockOn = true;
    lastSec = null;
    cancelAnimationFrame(raf);
    const loop = () => {
      if (!clockOn) return;
      tick();
      drawTimer(think);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
  }
  UI.stopClock = (finalMs) => {
    tick();
    clockOn = false;
    cancelAnimationFrame(raf);
    if (finalMs != null) drawTimer(finalMs);
  };

  /* ---------- 문제 ---------- */
  let locked = true, selected = -1, cur = null, seqId = 0, seqTimer = 0;
  const BARS = '<span class="bars"><i></i><i></i><i></i><i></i></span>';
  const audio = new Audio();  // 한 개를 계속 재사용 (사파리에서 첫 클릭 뒤 자동 재생이 막히지 않게)
  audio.preload = "auto";
  UI.setQuestion = (q) => {  // q = { ref, opts: [4개 소리 주소] }
    stop();
    cur = q; selected = -1;
    const box = $("choices");
    box.innerHTML = q.opts.map((src, i) =>
      `<button class="choice snd" data-i="${i}"><b>${i + 1}</b><span>소리 ${i + 1}</span>${BARS}</button>`).join("");
    box.querySelectorAll(".choice").forEach((b) => { b.onclick = () => pick(+b.dataset.i); });
    $("submit").disabled = true;
    [q.ref, ...q.opts].forEach((src) => { const a = new Audio(); a.preload = "auto"; a.src = src; });  // 미리 받아 두기
    if (!locked) startSeq();
  };
  UI.current = () => cur;  // 녹화 도구용: 지금 문제의 소리 주소
  function unmark() { document.querySelectorAll(".playing").forEach((e) => e.classList.remove("playing")); }
  function stop() {
    seqId += 1; clearTimeout(seqTimer);
    if (listening) setListening(false);
    audio.onended = audio.onerror = null;
    audio.pause();
    unmark();
  }
  function refLabel(t) { $("refBtn").querySelector(".t").textContent = t; }
  function startSeq() {  // 원본 → 소리 1 → 2 → 3 → 4
    if (!cur) return;
    stop();
    const id = seqId, tiles = $("choices").children;
    setListening(true);
    const items = [[$("refBtn"), cur.ref, "원본 소리"], ...cur.opts.map((src, i) => [tiles[i], src, `소리 ${i + 1} 나오는 중`])];
    $("refBtn").disabled = true;
    let k = 0;
    const next = () => {
      if (id !== seqId) return;
      unmark();
      if (k >= items.length) { setListening(false); refLabel("다시 듣기"); $("refBtn").classList.remove("dim"); $("refBtn").disabled = locked; window.__seqDone = true; return; }
      const [el, src, label] = items[k++];
      refLabel(label);
      el.classList.add("playing");
      if (k > 1) $("refBtn").classList.add("dim");
      const after = () => { if (id !== seqId) return; el.classList.remove("playing"); seqTimer = setTimeout(next, k === 1 ? 700 : 450); };
      audio.onended = after; audio.onerror = after;
      audio.src = src;
      const p = audio.play(); if (p && p.catch) p.catch(after);
    };
    window.__seqDone = false;
    $("refBtn").classList.remove("dim");
    next();
  }

  /* ---------- 라운드 ---------- */
  UI.beginRound = (onTimeout) => {
    hide("startScreen"); hide("resultScreen");
    renderStreak(0, false);
    locked = false;
    document.activeElement && document.activeElement.blur && document.activeElement.blur();
    startClock(onTimeout);
    startSeq();  // 시작 버튼을 누른 그 순간에 첫 소리를 틀어야 사파리도 재생을 허락한다
  };

  /* ---------- 정답/오답 효과 ---------- */
  const CHECK = "M50 86 L74 110 L120 60";
  const CROSS = "M60 60 L108 108 M108 60 L60 108";
  UI.feedback = (ok) => {
    const card = $("qcard");
    card.classList.remove("ok", "bad", "shake");
    void card.offsetWidth;
    card.classList.add(ok ? "ok" : "bad");
    if (!ok) card.classList.add("shake");
    clearTimeout(card._t);
    card._t = setTimeout(() => card.classList.remove("ok", "bad", "shake"), ok ? 450 : 750);

    const fx = $("fx");
    fx.className = "fx " + (ok ? "ok" : "bad");
    fx.innerHTML =
      `<div class="burst"><svg viewBox="0 0 168 168"><circle class="ring" cx="84" cy="84" r="80"/>` +
      `<g class="core"><circle class="bg" cx="84" cy="84" r="80"/><path d="${ok ? CHECK : CROSS}"/></g></svg></div>`;
    const dur = ok ? 640 : 1000;
    fx.querySelector(".burst").animate([
      { opacity: 0, transform: "scale(.5)" },
      { opacity: 1, transform: "scale(1.08)", offset: .22 },
      { opacity: 1, transform: "scale(1)", offset: .38 },
      { opacity: 1, transform: "scale(1)", offset: .74 },
      { opacity: 0, transform: "scale(.94)" },
    ], { duration: dur, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" });
    fx.querySelector("path").animate(
      [{ strokeDashoffset: 120 }, { strokeDashoffset: 0 }],
      { duration: 260, delay: 80, easing: "ease-out", fill: "forwards" });
    fx.querySelector(".ring").animate(
      [{ transform: "scale(1)", opacity: .9 }, { transform: "scale(1.9)", opacity: 0 }],
      { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" });
    if (ok) sparks(fx);

    const v = $("vignette");
    v.className = "vignette " + (ok ? "ok" : "");
    v.animate([{ opacity: 0 }, { opacity: 1, offset: .2 }, { opacity: 0 }], { duration: ok ? 520 : 850, easing: "ease-out" });
  };

  function sparks(host) {
    const n = 16;
    for (let i = 0; i < n; i++) {
      const s = document.createElement("i");
      s.className = "spark";
      s.style.background = i % 3 ? "var(--green)" : "#ffffff";
      const ang = (i / n) * Math.PI * 2 + Math.random() * .35;
      const dist = 200 + Math.random() * 150;
      host.appendChild(s);
      s.animate([
        { transform: "translate(0,0) scale(1)", opacity: 1 },
        { transform: `translate(${Math.cos(ang) * dist}px, ${Math.sin(ang) * dist - 30}px) scale(0)`, opacity: 0 },
      ], { duration: 620 + Math.random() * 260, easing: "cubic-bezier(.15,.8,.25,1)", fill: "forwards" }).onfinish = () => s.remove();
    }
  }

  /* ---------- 결과 ---------- */
  UI.showResult = ({ success, totalMs, maxStreak }) => {
    UI.stopClock();
    locked = true; stop(); $("submit").disabled = true; $("refBtn").disabled = true;
    setTimeout(() => {
      const icon = $("resultIcon");
      icon.setAttribute("class", "result-icon" + (success ? "" : " bad"));
      icon.innerHTML = `<circle class="ring" cx="90" cy="90" r="86"/><g class="core"><circle class="bg" cx="90" cy="90" r="86"/>` +
        `<path d="${success ? "M52 92 L79 119 L130 64" : "M64 64 L116 116 M116 64 L64 116"}"/></g>`;
      $("resultTitle").innerHTML = success ? "인간 인증<br><em style=\"color:var(--green)\">성공</em>" : "인간 인증<br><em style=\"color:var(--red)\">실패</em>";
      countUp($("rTime"), totalMs / 1000, 1, "초");  // 미션 3: 고르는 시간
      countUp($("rStreak"), maxStreak, 0, "문제");
      show("resultScreen");
      $("retryBtn").focus();
      if (success) confetti();
    }, success ? 700 : 500);
  };

  function countUp(el, value, digits, unit) {
    const start = performance.now(), dur = 700;
    const step = (now) => {
      const p = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = (value * e).toFixed(digits) + unit;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
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
      c.animate([
        { transform: "translate(0,0) rotate(0deg)", opacity: 1 },
        { transform: `translate(${drift}px, 105vh) rotate(${rot}deg)`, opacity: .9 },
      ], { duration: 2200 + Math.random() * 1400, delay: Math.random() * 350, easing: "cubic-bezier(.25,.5,.4,1)", fill: "forwards" })
        .onfinish = () => c.remove();
    }
  }

  /* ---------- 화면 전환 ---------- */
  function show(id) {
    const el = $(id);
    el.hidden = false;
    el.classList.remove("enter"); void el.offsetWidth; el.classList.add("enter");
  }
  function hide(id) { $(id).hidden = true; }
  const screenOpen = () => !$("startScreen").hidden || !$("resultScreen").hidden;

  UI.note = (text) => {
    const n = $("note");
    n.textContent = text;
    n.animate([{ opacity: 0, transform: "translate(-50%, 10px)" }, { opacity: 1, transform: "translate(-50%, 0)", offset: .15 },
               { opacity: 1, transform: "translate(-50%, 0)", offset: .8 }, { opacity: 0, transform: "translate(-50%, 0)" }],
              { duration: 1800, easing: "ease-out", fill: "forwards" });
  };

  /* ---------- 고르기 ---------- */
  UI.locked = () => locked;
  function pick(i) {  // 고르기만 한다 (소리는 자동으로 차례로 나옴)
    if (locked) return;
    const tiles = $("choices").children;
    if (!tiles[i]) return;
    selected = i;
    for (let k = 0; k < tiles.length; k++) tiles[k].classList.toggle("sel", k === i);
    $("submit").disabled = false;
  }
  function submit() {
    if (locked || selected < 0) return;
    const n = selected + 1;
    stop();
    emit("submit", String(n));
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("startBtn").onclick = () => emit("start");
    $("retryBtn").onclick = () => emit("start");
    $("refBtn").onclick = () => { if (!locked && !$("refBtn").disabled) startSeq(); };
    $("submit").onclick = () => submit();
    document.addEventListener("keydown", (e) => {
      if (screenOpen()) {
        if (e.key === "Enter") { e.preventDefault(); emit("start"); }
        else if (e.shiftKey && (e.key === "R" || e.key === "r")) { e.preventDefault(); emit("reset"); }
        else if (e.shiftKey && (e.key === "D" || e.key === "d")) { e.preventDefault(); emit("download"); }
        return;
      }
      if (["1", "2", "3", "4"].includes(e.key)) { e.preventDefault(); pick(+e.key - 1); }
      else if (e.key === " " || e.key === "0") { e.preventDefault(); if (!$("refBtn").disabled) startSeq(); }
      else if (e.key === "Enter") { e.preventDefault(); submit(); }
    });
  });

  window.UI = UI;
})();
