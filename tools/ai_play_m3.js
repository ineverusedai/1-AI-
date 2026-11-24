/* AI가 실제 게임 화면에서 미션 3(소리 착시 캡차)을 플레이하고, 화면과 소리를 함께 1920×1200 60fps 로 녹화한다.
 *
 * 화면은 문제마다 원본 → 소리 1 → 2 → 3 → 4 를 자동으로 차례로 튼다 (IllusionAudio 방식, 사람과 같음).
 * AI의 "손과 귀": 차례 재생이 끝날 때까지 기다린 뒤 → 원본과 사인파 소리 4개의 파일을 solver.py 에 넘겨 답(1~4)을 받고
 * → 그 소리 칸을 누르고 → 확인. solver.py 는 소리 바이트만 받는다 (정답·시드·키를 모름).
 * 소리: 페이지의 재생 요청을 시각과 함께 기록해 두었다가, 녹화가 끝난 뒤 같은 시각에 그 소리 파일을 깔아 영상에 합친다.
 * 영상 속 시간 = 실제로 재생한 소리 길이 + AI가 실제로 계산한 시간.
 *
 * 실행 (프로젝트 폴더에서, 먼저 python -m tools.build_web):
 *   node tools/ai_play_m3.js --solver <solver.py 폴더> [--out results/videos] [--mode B]
 */
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? acc.concat([[v.slice(2), a[i + 1]]]) : acc), []));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(args.port || 8782);
const MODE = args.mode || "B";
const OUT = path.resolve(args.out || path.join(ROOT, "results", "videos"));
const FPS = Number(args.fps || 60);
const GAP_MS = Number(args["gap-ms"] || 250);
const CSS_W = 1440, CSS_H = 900, OUT_W = Number(args.width || 1920);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const children = [];
process.on("exit", () => children.forEach((c) => { try { c.kill(); } catch {} }));
process.on("SIGINT", () => process.exit(130));

function startSolver() {
  const p = spawn("python3", ["-I", path.join(ROOT, "tools", "solver_bridge.py"), path.resolve(args.solver)], { stdio: ["pipe", "pipe", "inherit"] });
  const rl = readline.createInterface({ input: p.stdout });
  const queue = [];
  rl.on("line", (line) => { const r = queue.shift(); r && r(JSON.parse(line)); });
  const next = () => new Promise((r) => queue.push(r));
  const ask = (ref, opts) => { const pr = next(); p.stdin.write(JSON.stringify({ ref_b64: ref.toString("base64"), opts_b64: opts.map((b) => b.toString("base64")) }) + "\n"); return pr; };
  return { proc: p, ready: next(), ask };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const web = spawn("python3", ["-m", "http.server", String(PORT), "--bind", "127.0.0.1", "--directory", path.join(ROOT, "docs")], { stdio: "ignore" });
  const solver = startSolver();
  children.push(web, solver.proc);
  await solver.ready;
  const wd = path.join(ROOT, "data", "m3", "audio", "q24");
  await solver.ask(fs.readFileSync(path.join(wd, "ref.wav")), [1, 2, 3, 4].map((n) => fs.readFileSync(path.join(wd, `opt${n}.wav`))));  // 예열 (게임 밖, 마지막 문제)
  const wavDur = (file) => { const b = fs.readFileSync(file); const sr = b.readUInt32LE(24), bps = b.readUInt16LE(34) / 8 * b.readUInt16LE(22);
    let o = 12; while (o < b.length - 8) { const id = b.toString("ascii", o, o + 4), sz = b.readUInt32LE(o + 4); if (id === "data") return sz / bps / sr; o += 8 + sz; } return 0; };
  const DUR = {};
  for (const d of fs.readdirSync(path.join(ROOT, "docs", "m3", "audio"))) for (const f of fs.readdirSync(path.join(ROOT, "docs", "m3", "audio", d))) DUR[`audio/${d}/${f}`] = wavDur(path.join(ROOT, "docs", "m3", "audio", d, f));

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: CSS_W, height: CSS_H }, deviceScaleFactor: OUT_W / CSS_W });
  const page = await ctx.newPage();
  await page.clock.install({ time: Date.now() });
  // 소리 재생을 가로채서 시각을 기록하고, 실제 재생 대신 페이지 시계로 소리 길이만큼 뒤에 'ended' 를 보낸다
  await page.addInitScript((DUR) => {
    window.__plays = [];
    const key = (src) => src.slice(src.indexOf("audio/"));
    HTMLMediaElement.prototype.play = function () {
      if (this.__rec && this.__rec.end === null) this.__rec.end = performance.now();
      const k = key(this.src), d = DUR[k] || 0;
      window.__plays.push({ src: k, t: performance.now(), end: null });
      this.__rec = window.__plays[window.__plays.length - 1];
      clearTimeout(this.__t);
      this.__t = setTimeout(() => { this.__rec.end = performance.now(); this.dispatchEvent(new Event("ended")); }, d * 1000);
      return Promise.resolve();
    };
    HTMLMediaElement.prototype.pause = function () {
      clearTimeout(this.__t);
      if (this.__rec && this.__rec.end === null) this.__rec.end = performance.now();
    };
  }, DUR);
  // CSS·WAAPI 애니메이션도 페이지 시계에 맞춰 멈췄다가 프레임마다 정확한 위치로 옮긴다
  await page.addInitScript(() => {
    const starts = new WeakMap();
    window.__syncAnimations = () => {
      const now = performance.now();
      for (const a of document.getAnimations()) {
        if (!starts.has(a)) { starts.set(a, now); a.pause(); }
        a.currentTime = (now - starts.get(a)) * (a.playbackRate || 1);
      }
    };
  });

  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), "m3-frames-"));
  let vt = 0, frame = 0;  // vt: 페이지 시계 (ms, 녹화 시작부터)
  const frameAt = (k) => Math.round((k * 1000) / FPS);
  async function shoot() {
    await page.evaluate(() => window.__syncAnimations());
    await page.screenshot({ path: path.join(framesDir, String(frame).padStart(6, "0") + ".png"), caret: "hide" });
    frame += 1;
  }
  async function advanceTo(T) {  // 페이지 시계를 T까지 넘기면서 그 사이 프레임을 모두 찍는다
    T = Math.round(T);
    while (frameAt(frame) <= T) {
      const target = frameAt(frame);
      if (target > vt) { await page.clock.runFor(target - vt); vt = target; }
      await shoot();
    }
    if (T > vt) { await page.clock.runFor(T - vt); vt = T; }
  }
  async function until(fn, arg) {  // 실제 시간으로 기다림 (이미지 로딩 등). 페이지 시계는 멈춰 있음
    for (let i = 0; i < 4000; i++) { const v = await page.evaluate(fn, arg); if (v) return v; await sleep(2); }
    throw new Error("기다리다 시간 초과");
  }

  for (let i = 0; i < 50; i++) { try { await page.goto(`http://127.0.0.1:${PORT}/m3/index.html?who=claude&mode=${MODE}`); break; } catch { await sleep(200); } }
  await page.evaluate(() => { try { localStorage.clear(); } catch {} });  // 이 녹화용 브라우저의 예전 기록 지우기
  await page.reload();
  await page.evaluate(() => Promise.all([document.fonts.load('700 40px "Pretendard HV"', "가A0"), document.fonts.load('700 40px "JetBrains Mono HV"', "A0")]));
  await until(() => document.fonts.status === "loaded" && document.fonts.check('700 40px "Pretendard HV"', "가") && document.fonts.check('700 40px "JetBrains Mono HV"', "A"));
  // 페이지 시계를 멈춘다. 이제부터 페이지 시간은 advanceTo 로만 흐른다
  await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 100);
  const pageT0 = await page.evaluate(() => performance.now());  // 영상 0초 = 이 페이지 시각
  await advanceTo(2500);                                   // 시작 화면

  const log = [];
  await page.keyboard.press("Enter");                    // 시작 화면에서 Enter = 시작하기 (클릭은 멈춘 시계와 충돌)
  let prevSrc = null;
  while (true) {
    const st = await until((prev) => {
      if (!document.getElementById("resultScreen").hidden || UI.locked()) return { done: true };
      const q = UI.current && UI.current();
      return q && q.ref !== prev ? { src: q.ref, ref: q.ref, opts: q.opts } : false;
    }, prevSrc);
    if (st.done) break;
    prevSrc = st.src;
    const center = async (sel) => page.evaluate((sel) => { const b = document.querySelector(sel).getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; }, sel);
    // 1) 화면이 원본 → 소리 1~4 를 차례로 다 틀 때까지 (페이지 시계로) 기다림
    for (let i = 0; i < 6000 && !(await page.evaluate(() => window.__seqDone)); i++) await advanceTo(vt + 1000 / FPS);
    await advanceTo(vt + GAP_MS);
    // 2) AI가 실제로 분석한 시간만큼
    const t0 = performance.now();
    const buf = async (u) => Buffer.from(await (await ctx.request.get(`http://127.0.0.1:${PORT}/m3/${u}`)).body());
    const r = await solver.ask(await buf(st.ref), await Promise.all(st.opts.map(buf)));
    const thinkMs = performance.now() - t0;
    await advanceTo(vt + thinkMs);
    // 3) 고른 소리 칸을 누르고 → 확인
    const n = Math.max(1, Math.min(4, parseInt(r.answer, 10) || 1));
    let c = await center(`#choices .choice:nth-child(${n})`);
    await page.mouse.move(c.x, c.y); await advanceTo(vt + GAP_MS);
    await page.mouse.down(); await page.mouse.up();
    await advanceTo(vt + GAP_MS);
    c = await center("#submit");
    await page.mouse.move(c.x, c.y); await advanceTo(vt + GAP_MS);
    await page.mouse.down(); await page.mouse.up();
    log.push({ video_ms: vt, question: st.ref.split("/")[1], answer: n, solve_ms: r.ms, think_ms: +thinkMs.toFixed(1) });
    await advanceTo(vt + 1000 / FPS);
    if (vt > 120000) break;
  }
  await advanceTo(vt + 6500);                              // 결과 화면 + 꽃가루

  const result = await page.evaluate(() => ({
    title: document.getElementById("resultTitle").textContent.replace(/\s+/g, " ").trim(),
    time: document.getElementById("rTime").textContent, streak: document.getElementById("rStreak").textContent,
    plays: window.__plays,
  }));
  const records = await page.evaluate(() => HV.records.dump());
  await browser.close();

  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  const base = path.join(OUT, `m3_claude_${MODE}_${stamp}`);
  // 소리 트랙: 재생 기록대로 소리 파일을 깔아 한 개의 wav 로 만든 뒤 영상과 합친다
  const plays = result.plays.map((p) => ({ src: path.join(ROOT, "docs", "m3", p.src), start: (p.t - pageT0) / 1000, end: p.end == null ? null : (p.end - pageT0) / 1000 }));
  delete result.plays;
  const plan = path.join(framesDir, "plays.json"), mix = path.join(framesDir, "mix.wav");
  fs.writeFileSync(plan, JSON.stringify({ plays, total: frame / FPS }));
  execFileSync("python3", ["-m", "tools.mix_audio", plan, mix], { cwd: ROOT, stdio: "inherit" });
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(framesDir, "%06d.png"), "-i", mix,
    "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", base + ".mp4"]);
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.writeFileSync(base + ".json", JSON.stringify({ result, fps: FPS, gap_ms: GAP_MS, size: `${OUT_W}x${Math.round(OUT_W * CSS_H / CSS_W)}`, frames: frame, log, records }, null, 1));
  if (!("no-record" in args)) execFileSync("python3", ["-m", "tools.import_web_records", base + ".json"], { cwd: ROOT, stdio: "inherit" });  // 시험 녹화는 --no-record
  console.log(JSON.stringify({ result, answered: log.length, frames: frame, video: base + ".mp4" }, null, 1));
  process.exit(0);  // 풀이 프로그램·웹 서버 자식 프로세스까지 정리하고 끝냄
})().catch((e) => { console.error(e); process.exit(1); });
