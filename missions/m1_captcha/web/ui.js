/* 미션 1 화면과 효과. 채점·기록은 engine.js 가 맡는다 (웹 버전 / Python 서버 버전이 이 파일을 같이 씀).
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
    limitMs = limitSec * 1000;
    target = streakTarget;
    $("target").textContent = target;
    $("startHead").innerHTML = `<em>${limitSec}초</em> 안에<br>${target}문제 연속으로 맞히세요`;
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
  function drawTimer(ms) {
    const left = Math.max(0, limitMs - ms);
    const cls = left <= 10000 ? "crit" : left <= 20000 ? "low" : "";
    const el = $("timer");
    el.firstChild.nodeValue = (left / 1000).toFixed(1);
    el.classList.toggle("low", cls === "low");
    el.classList.toggle("crit", cls === "crit");
    $("timebar").className = "timebar " + cls;
    $("timefill").style.transform = `scaleX(${left / limitMs})`;
    const sec = Math.ceil(left / 1000);
    if (clockOn && cls === "crit" && left > 0 && sec !== lastSec) {  // 마지막 10초: 1초마다 숫자가 살짝 튐
      el.classList.remove("pulse"); void el.offsetWidth; el.classList.add("pulse");
    }
    lastSec = sec;
  }
  UI.elapsed = () => performance.now() - t0;
  function startClock(onTimeout) {
    t0 = performance.now();
    clockOn = true;
    lastSec = null;
    cancelAnimationFrame(raf);
    const loop = () => {
      if (!clockOn) return;
      const ms = performance.now() - t0;
      if (ms >= limitMs) { clockOn = false; drawTimer(limitMs); onTimeout && onTimeout(); return; }
      drawTimer(ms);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
  }
  UI.stopClock = (finalMs) => {
    clockOn = false;
    cancelAnimationFrame(raf);
    if (finalMs != null) drawTimer(finalMs);
  };

  /* ---------- 문제 ---------- */
  UI.setQuestion = (src, preload) => {
    const img = $("img");
    img.classList.add("swap");
    img.onload = () => img.classList.remove("swap");
    img.src = src;
    if (preload) new Image().src = preload;
  };

  /* ---------- 라운드 ---------- */
  UI.beginRound = (onTimeout) => {
    hide("startScreen"); hide("resultScreen");
    renderStreak(0, false);
    $("answer").disabled = false; $("submit").disabled = false;
    $("answer").value = "";
    $("answer").focus();
    startClock(onTimeout);
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
    $("answer").disabled = true; $("submit").disabled = true;
    setTimeout(() => {
      const icon = $("resultIcon");
      icon.setAttribute("class", "result-icon" + (success ? "" : " bad"));
      icon.innerHTML = `<circle class="ring" cx="90" cy="90" r="86"/><g class="core"><circle class="bg" cx="90" cy="90" r="86"/>` +
        `<path d="${success ? "M52 92 L79 119 L130 64" : "M64 64 L116 116 M116 64 L64 116"}"/></g>`;
      $("resultTitle").innerHTML = success ? "인간 인증<br><em style=\"color:var(--green)\">성공</em>" : "인간 인증<br><em style=\"color:var(--red)\">실패</em>";
      countUp($("rTime"), totalMs / 1000, 1, "초");
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

  /* ---------- 입력 ---------- */
  function submit() {
    if ($("answer").disabled) return;
    const val = $("answer").value.trim();
    if (!val) return;
    $("answer").value = "";
    emit("submit", val);
  }
  document.addEventListener("DOMContentLoaded", () => {
    $("startBtn").onclick = () => emit("start");
    $("retryBtn").onclick = () => emit("start");
    $("submit").onclick = () => { submit(); $("answer").focus(); };
    $("answer").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submit(); } });
    document.addEventListener("keydown", (e) => {
      if (!screenOpen()) return;
      if (e.key === "Enter") { e.preventDefault(); emit("start"); }
      else if (e.shiftKey && (e.key === "R" || e.key === "r")) { e.preventDefault(); emit("reset"); }
      else if (e.shiftKey && (e.key === "D" || e.key === "d")) { e.preventDefault(); emit("download"); }
    });
  });

  window.UI = UI;
})();
