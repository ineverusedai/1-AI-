/* AI가 실제 게임 화면에서 미션 2(착시 캡차)를 플레이하고, 그 화면을 1920×1200 60fps 로 녹화한다.
 *
 * 이 스크립트는 AI의 "손과 눈"만 맡는다:
 *   화면에 뜬 그림과 선택지 4개를 가져와 → AI가 만든 solver.py 에 넘기고 → 돌아온 답의 선택지에 마우스를 올렸다가 클릭.
 *   solver.py 는 그림 바이트와 선택지 글자만 받는다 (정답·시드·키·페이지 소스를 모름).
 *
 * 녹화 방식은 ai_play_m1.js 와 같다 (페이지 시계를 쥐고 1/60초씩 넘기며 매 프레임 촬영, 영상 속 시간 = AI가 실제로 걸린 시간).
 * 고르는 모습: 답을 낸 뒤 그 선택지에 마우스를 --hover-ms 동안 올려 두었다가 클릭 (보는 사람이 어떤 걸 골랐는지 보이게).
 *
 * 실행 (프로젝트 폴더에서, 먼저 python -m tools.build_web):
 *   node tools/ai_play_m2.js --solver <solver.py 폴더> [--out results/videos] [--mode B] [--hover-ms 150]
 */
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? acc.concat([[v.slice(2), a[i + 1]]]) : acc), []));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(args.port || 8781);
const MODE = args.mode || "B";
const OUT = path.resolve(args.out || path.join(ROOT, "results", "videos"));
const FPS = Number(args.fps || 60);
const HOVER_MS = Number(args["hover-ms"] || 150);
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
  const ask = (buf, choices) => { const pr = next(); p.stdin.write(JSON.stringify({ png_b64: buf.toString("base64"), choices }) + "\n"); return pr; };
  return { proc: p, ready: next(), ask };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const web = spawn("python3", ["-m", "http.server", String(PORT), "--bind", "127.0.0.1", "--directory", path.join(ROOT, "docs")], { stdio: "ignore" });
  const solver = startSolver();
  children.push(web, solver.proc);
  await solver.ready;
  const warm = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "m2", "manifest.json"), "utf8")).questions.slice(-1)[0];
  await solver.ask(fs.readFileSync(path.join(ROOT, "data", "m2", "images", warm.file)), warm.choices);  // 모델 예열 (게임 밖)

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

  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), "m2-frames-"));
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

  for (let i = 0; i < 50; i++) { try { await page.goto(`http://127.0.0.1:${PORT}/m2/index.html?who=claude&mode=${MODE}`); break; } catch { await sleep(200); } }
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
      if (!document.getElementById("resultScreen").hidden || UI.locked()) return { done: true };
      const img = document.getElementById("img");
      const choices = [...document.querySelectorAll("#choices .choice span")].map((e) => e.textContent);
      return img.src && img.src !== prev && img.complete && img.naturalWidth && choices.length === 4 ? { src: img.src, choices } : false;
    }, prevSrc);
    if (st.done) break;
    prevSrc = st.src;
    // ---- 여기서부터 AI가 실제로 걸린 시간을 재서 그만큼 영상 시간을 흘린다 ----
    const t0 = performance.now();
    const png = Buffer.from(await (await ctx.request.get(st.src)).body());  // 화면에 뜬 그 이미지
    const r = await solver.ask(png, st.choices);
    const thinkMs = performance.now() - t0;
    await advanceTo(vt + thinkMs);
    const idx = st.choices.indexOf(r.answer);
    const box = await page.evaluate((i) => { const b = document.querySelectorAll("#choices .choice")[i].getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; }, Math.max(0, idx));
    const hoverStart = vt;
    await page.mouse.move(box.x, box.y);                  // 고른 선택지에 마우스를 올려 보여 줌
    await advanceTo(vt + HOVER_MS);
    await page.mouse.down(); await page.mouse.up();        // 클릭
    log.push({ video_ms: vt, image: st.src.split("/").pop(), choices: st.choices, answer: r.answer, solve_ms: r.ms, think_ms: +thinkMs.toFixed(1), hover_ms: vt - hoverStart });
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
  const base = path.join(OUT, `m2_claude_${MODE}_${stamp}`);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(framesDir, "%06d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", base + ".mp4"]);
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.writeFileSync(base + ".json", JSON.stringify({ result, fps: FPS, hover_ms: HOVER_MS, size: `${OUT_W}x${Math.round(OUT_W * CSS_H / CSS_W)}`, frames: frame, log, records }, null, 1));
  if (!("no-record" in args)) execFileSync("python3", ["-m", "tools.import_web_records", base + ".json"], { cwd: ROOT, stdio: "inherit" });  // 시험 녹화는 --no-record
  console.log(JSON.stringify({ result, answered: log.length, frames: frame, video: base + ".mp4" }, null, 1));
  process.exit(0);  // 풀이 프로그램·웹 서버 자식 프로세스까지 정리하고 끝냄
})().catch((e) => { console.error(e); process.exit(1); });
