/* AI가 실제 게임 화면에서 미션 1을 플레이하고, 그 화면을 1920×1200 60fps 로 녹화한다.
 *
 * 이 스크립트는 AI의 "손과 눈"만 맡는다:
 *   화면에 뜬 캡차 이미지를 가져와 → AI가 만든 solver.py 에 넘기고 → 돌아온 답을 입력칸에 치고 Enter.
 *   solver.py 는 이미지 바이트만 받는다 (정답·시드·키·페이지 소스를 모름).
 *
 * 녹화 방식 (프레임 정확 녹화):
 *   게임 페이지의 시계(타이머·애니메이션)를 이 스크립트가 쥐고 1/60초씩 넘기며 매 프레임을 찍는다.
 *   AI가 문제를 보고 답을 내기까지 실제로 걸린 시간만큼 페이지 시계도 흘려보낸다.
 *   → 컴퓨터 성능과 상관없이 끊김 없는 60fps, 영상 속 시간 = 실제 AI가 걸린 시간.
 *
 * 화면 크기: 맥북 기본(1440×900, 16:10)으로 배치하고 1920×1200 으로 찍는다.
 * 결과: <out>/m1_claude_<방식>_<시각>.mp4 (+ 프레임별 기록 .json), results/ 에 who=claude 로 기록.
 *
 * 실행 (프로젝트 폴더에서, 먼저 python -m tools.build_web):
 *   node tools/ai_play_m1.js --solver <solver.py 폴더> [--out results/videos] [--mode B] [--char-ms 45] [--hold-ms 200]
 *
 * 입력 모습: 답을 낸 뒤 글자를 한 글자씩(--char-ms 간격) 입력칸에 치고, 다 친 답을 --hold-ms 동안 보여 준 뒤 Enter.
 *   AI의 실제 타자는 몇 밀리초라 영상에서 안 보이므로, 보는 사람이 읽을 수 있게 일부러 이만큼 천천히 친다.
 *   이 타자 시간은 게임 시계에도 그대로 들어간다 (기록의 think_ms = AI가 실제로 보고 답을 낸 시간).
 */
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? acc.concat([[v.slice(2), a[i + 1]]]) : acc), []));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(args.port || 8780);
const MODE = args.mode || "B";
const OUT = path.resolve(args.out || path.join(ROOT, "results", "videos"));
const FPS = Number(args.fps || 60);
const CHAR_MS = Number(args["char-ms"] || 45), HOLD_MS = Number(args["hold-ms"] || 200);
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
  const ask = (buf) => { const pr = next(); p.stdin.write(JSON.stringify({ png_b64: buf.toString("base64") }) + "\n"); return pr; };
  return { proc: p, ready: next(), ask };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const web = spawn("python3", ["-m", "http.server", String(PORT), "--bind", "127.0.0.1", "--directory", path.join(ROOT, "docs")], { stdio: "ignore" });
  const solver = startSolver();
  children.push(web, solver.proc);
  await solver.ready;
  await solver.ask(fs.readFileSync(path.join(ROOT, "data", "m1", "images", "q200.png")));  // 모델 예열 (게임 밖)

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: CSS_W, height: CSS_H }, deviceScaleFactor: OUT_W / CSS_W });
  const page = await ctx.newPage();
  await page.clock.install({ time: Date.now() });
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

  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), "m1-frames-"));
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

  for (let i = 0; i < 50; i++) { try { await page.goto(`http://127.0.0.1:${PORT}/m1/index.html?who=claude&mode=${MODE}`); break; } catch { await sleep(200); } }
  await page.evaluate(() => { try { localStorage.clear(); } catch {} });  // 이 녹화용 브라우저의 예전 기록 지우기
  await page.reload();
  await page.evaluate(() => Promise.all([document.fonts.load('700 40px "Pretendard HV"', "가A0"), document.fonts.load('700 40px "JetBrains Mono HV"', "A0")]));
  await until(() => document.fonts.status === "loaded" && document.fonts.check('700 40px "Pretendard HV"', "가") && document.fonts.check('700 40px "JetBrains Mono HV"', "A"));
  // 페이지 시계를 멈춘다. 이제부터 페이지 시간은 advanceTo 로만 흐른다
  await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 100);
  await advanceTo(2500);                                   // 시작 화면

  const log = [];
  await page.keyboard.press("Enter");                    // 시작 화면에서 Enter = 시작하기 (클릭은 멈춘 시계와 충돌)
  let prevSrc = null;
  while (true) {
    const st = await until((prev) => {
      if (document.getElementById("answer").disabled) return { done: true };
      const img = document.getElementById("img");
      return img.src && img.src !== prev && img.complete && img.naturalWidth ? { src: img.src } : false;
    }, prevSrc);
    if (st.done) break;
    prevSrc = st.src;
    // ---- 여기서부터 AI가 실제로 걸린 시간을 재서 그만큼 영상 시간을 흘린다 ----
    const t0 = performance.now();
    const png = Buffer.from(await (await ctx.request.get(st.src)).body());  // 화면에 뜬 그 이미지
    const r = await solver.ask(png);
    const thinkMs = performance.now() - t0;
    await advanceTo(vt + thinkMs);
    const typeStart = vt;
    for (const ch of r.answer) {                           // 한 글자씩 쳐서 입력되는 모습이 보이게
      await page.press("#answer", ch);
      await advanceTo(vt + CHAR_MS);
    }
    await advanceTo(vt + HOLD_MS);                         // 다 친 답을 잠깐 보여 줌
    await page.press("#answer", "Enter");
    log.push({ video_ms: vt, image: st.src.split("/").pop(), answer: r.answer, solve_ms: r.ms, think_ms: +thinkMs.toFixed(1), type_ms: vt - typeStart });
    await advanceTo(vt + 1000 / FPS);
    if (vt > 70000) break;
  }
  await advanceTo(vt + 6500);                              // 결과 화면 + 꽃가루

  const result = await page.evaluate(() => ({
    title: document.getElementById("resultTitle").textContent.replace(/\s+/g, " ").trim(),
    time: document.getElementById("rTime").textContent, streak: document.getElementById("rStreak").textContent,
  }));
  const records = await page.evaluate(() => HV.records.dump());
  await browser.close();

  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  const base = path.join(OUT, `m1_claude_${MODE}_${stamp}`);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(framesDir, "%06d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", base + ".mp4"]);
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.writeFileSync(base + ".json", JSON.stringify({ result, fps: FPS, char_ms: CHAR_MS, hold_ms: HOLD_MS, size: `${OUT_W}x${Math.round(OUT_W * CSS_H / CSS_W)}`, frames: frame, log, records }, null, 1));
  execFileSync("python3", ["-m", "tools.import_web_records", base + ".json"], { cwd: ROOT, stdio: "inherit" });
  console.log(JSON.stringify({ result, answered: log.length, frames: frame, video: base + ".mp4" }, null, 1));
  process.exit(0);  // 풀이 프로그램·웹 서버 자식 프로세스까지 정리하고 끝냄
})().catch((e) => { console.error(e); process.exit(1); });
