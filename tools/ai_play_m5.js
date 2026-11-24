/* 미션 5 AI 플레이 리플레이 녹화: AI가 tools/arc_play.py 로 실제로 한 행동 기록(log.jsonl)을
 * 사람용 웹 게임 화면에서 그대로 다시 입력하면서 1920×1200 60fps 로 찍는다 (같은 게임 파일·엔진이라 결과가 같다).
 *
 * 타임랩스: AI가 생각하던 시간(행동 사이 실제 간격)은 페이지 시계만 그만큼 흘려보내고 화면은 건너뛴다.
 * 그래서 화면 위 남은 시간은 실제 시각 그대로 줄고, 영상은 행동마다 --show-ms 만큼만 보여 준다.
 * 화면 왼쪽 위에 "AI 리플레이 · 생각하는 시간은 건너뜀" 표시를 붙인다.
 *
 * 실행 (프로젝트 폴더에서, 먼저 python -m tools.build_web):
 *   node tools/ai_play_m5.js --log <log.jsonl> [--out results/videos] [--show-ms 400]
 */
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? acc.concat([[v.slice(2), a[i + 1]]]) : acc), []));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(args.port || 8785);
const OUT = path.resolve(args.out || path.join(ROOT, "results", "videos"));
const FPS = 60, SHOW_MS = Number(args["show-ms"] || 400);
const CSS_W = 1440, CSS_H = 900, OUT_W = 1920;
const KEYS = { 0: "r", 1: "ArrowUp", 2: "ArrowDown", 3: "ArrowLeft", 4: "ArrowRight", 5: " ", 7: "z" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const children = [];
process.on("exit", () => children.forEach((c) => { try { c.kill(); } catch {} }));

(async () => {
  const log = fs.readFileSync(path.resolve(args.log), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  const t0 = log[0].t;
  fs.mkdirSync(OUT, { recursive: true });
  const web = spawn("python3", ["-m", "http.server", String(PORT), "--bind", "127.0.0.1", "--directory", path.join(ROOT, "docs")], { stdio: "ignore" });
  children.push(web);
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: CSS_W, height: CSS_H }, deviceScaleFactor: OUT_W / CSS_W });
  const page = await ctx.newPage();
  await page.clock.install({ time: Date.now() });
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
  for (let i = 0; i < 50; i++) { try { await page.goto(`http://127.0.0.1:${PORT}/m5/index.html?who=claude&mode=A`); break; } catch { await sleep(200); } }
  await page.evaluate(() => { try { localStorage.clear(); } catch {} });
  await page.reload();
  for (let i = 0; i < 600; i++) { if (await page.evaluate(() => window.M5 && M5.ready() && document.fonts.status === "loaded")) break; await sleep(200); }
  await page.evaluate(() => {
    const b = document.createElement("div");
    b.textContent = "AI 리플레이 · 생각하는 시간은 건너뜀";
    b.style.cssText = "position:fixed;left:24px;top:18px;z-index:50;padding:8px 16px;border-radius:999px;background:rgba(49,130,246,.18);color:#8fbaff;font-weight:800;font-size:18px;letter-spacing:-.02em";
    document.body.appendChild(b);
  });
  await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 100);

  const framesDir = fs.mkdtempSync(path.join(os.tmpdir(), "m5-frames-"));
  let frame = 0, vt = 0;
  async function shoot() {
    await page.evaluate(() => window.__syncAnimations());
    await page.screenshot({ path: path.join(framesDir, String(frame).padStart(6, "0") + ".png"), caret: "hide" });
    frame += 1;
  }
  async function film(ms) {  // ms 동안 1/60초씩 찍기
    for (let k = 0; k < Math.round(ms * FPS / 1000); k++) { await page.clock.runFor(1000 / FPS); vt += 1000 / FPS; await shoot(); }
  }
  async function skipTo(T) { if (T > vt) { await page.clock.runFor(T - vt); vt = T; } }
  async function waitIdle() { for (let i = 0; i < 400 && await page.evaluate(() => M5.busy()); i++) { await page.clock.runFor(50); vt += 50; } }

  await film(2000);                                   // 시작 화면
  await page.keyboard.press("Enter");
  const startVt = vt;
  await film(800);
  const box = await page.locator("#arc").boundingBox();
  let n = 0;
  for (const e of log) {
    if (e.kind === "start") continue;
    await skipTo(startVt + (e.t - t0) * 1000);      // 생각한 시간: 시계만 흘림
    await waitIdle();
    if (e.kind === "switch") await page.keyboard.press(String(e.game + 1));
    else if (e.action === 6) await page.mouse.click(box.x + (e.x + 0.5) * box.width / 64, box.y + (e.y + 0.5) * box.height / 64);
    else await page.keyboard.press(KEYS[e.action]);
    n += e.kind === "act" ? 1 : 0;
    await film(SHOW_MS);
  }
  await waitIdle();
  await film(1500);
  const status = await page.evaluate(() => M5.status());
  await browser.close();

  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  const base = path.join(OUT, `m5_claude_A_replay_${stamp}`);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(framesDir, "%06d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", base + ".mp4"]);
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.writeFileSync(base + ".json", JSON.stringify({ status, actions: n, real_sec: log[log.length - 1].t - t0, frames: frame, show_ms: SHOW_MS }, null, 1));
  console.log(JSON.stringify({ status, actions: n, frames: frame, video: base + ".mp4" }, null, 1));
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
