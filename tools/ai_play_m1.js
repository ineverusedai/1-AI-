/* AI가 실제 게임 화면(Python 서버 버전)에서 미션 1을 플레이하고 그 화면을 녹화한다.
 *
 * 이 스크립트는 AI의 "손과 눈"만 맡는다:
 *   화면의 캡차 이미지를 가져와 → AI가 만든 solver.py 에 넘기고 → 돌아온 답을 입력칸에 치고 Enter.
 * 채점은 서버가 하고, 결과는 results/ 에 who=claude 로 기록된다.
 * 서버 버전을 쓰는 이유: 정답 해시와 키가 서버에만 있어서 페이지 소스로는 답을 알 수 없다.
 *
 * 실행 (프로젝트 폴더에서):
 *   node tools/ai_play_m1.js --solver <solver.py 폴더> --out <영상 저장 폴더> [--mode B] [--font <pretendard 패키지 폴더>]
 */
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const readline = require("readline");

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? acc.concat([[v.slice(2), a[i + 1]]]) : acc), []));
const ROOT = path.resolve(__dirname, "..");
const PORT = Number(args.port || 8770);
const MODE = args.mode || "B";
const OUT = path.resolve(args.out || path.join(ROOT, "results", "videos"));
const W = 1600, H = 900;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function startServer() {
  const p = spawn("python3", ["run.py", "--port", String(PORT), "--no-browser"], { cwd: ROOT, stdio: "ignore" });
  return p;
}

function startSolver() {
  const p = spawn("python3", ["-I", path.join(ROOT, "tools", "solver_bridge.py"), path.resolve(args.solver)], { stdio: ["pipe", "pipe", "inherit"] });
  const rl = readline.createInterface({ input: p.stdout });
  const queue = [];
  rl.on("line", (line) => { const r = queue.shift(); r && r(JSON.parse(line)); });
  const next = () => new Promise((r) => queue.push(r));
  const ask = (buf) => { const pr = next(); p.stdin.write(JSON.stringify({ png_b64: buf.toString("base64") }) + "\n"); return pr; };
  return { proc: p, ready: next(), ask };
}

const children = [];
const cleanup = () => children.forEach((c) => { try { c.kill(); } catch {} });
process.on("exit", cleanup);
process.on("SIGINT", () => process.exit(130));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const server = startServer();
  const solver = startSolver();
  children.push(server, solver.proc);
  await solver.ready;
  // 모델 예열 (게임 시작 전에 한 번 돌려서 첫 문제가 느리지 않게)
  const warm = fs.readFileSync(path.join(ROOT, "data", "m1", "images", "q200.png"));
  await solver.ask(warm);
  await sleep(1200);

  const browser = await chromium.launch();
  const tmpVideo = fs.mkdtempSync(path.join(OUT, ".rec-"));
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, recordVideo: { dir: tmpVideo, size: { width: W, height: H } } });
  if (args.font) {  // 글꼴 사이트가 막힌 환경에서도 같은 글꼴로 녹화
    const base = path.resolve(args.font, "dist", "web", "variable");
    await ctx.route(/cdn\.jsdelivr\.net\/gh\/orioncactus\/pretendard@v1\.3\.9\/dist\/web\/variable\/(.*)$/, (route) => {
      const rel = route.request().url().split("/dist/web/variable/")[1].split("?")[0];
      const file = path.join(base, rel);
      if (!fs.existsSync(file)) return route.abort();
      route.fulfill({ path: file, contentType: rel.endsWith(".css") ? "text/css" : "font/woff2" });
    });
  }
  const page = await ctx.newPage();
  const url = `http://127.0.0.1:${PORT}/m1/?who=claude&mode=${MODE}`;
  for (let i = 0; i < 20; i++) { try { await page.goto(url); break; } catch { await sleep(300); } }
  await page.evaluate(() => document.fonts.ready);
  await sleep(2500);                       // 시작 화면 잠깐 보여주기

  const log = [];
  await page.click("#startBtn");
  await page.waitForSelector("#answer:not([disabled])");
  const t0 = Date.now();
  let prevSrc = null;
  while (true) {
    // 새 문제 이미지가 뜰 때까지 (또는 결과 화면이 뜰 때까지) 기다림
    const state = await page.waitForFunction((prev) => {
      if (!document.getElementById("resultScreen").hidden) return { done: true };
      if (document.getElementById("answer").disabled) return false;  // 끝나는 중: 결과 화면을 기다림
      const img = document.getElementById("img");
      if (img.src && img.src !== prev && img.complete && img.naturalWidth) return { src: img.src };
      return false;
    }, prevSrc, { polling: 10, timeout: 70000 }).then((h) => h.jsonValue());
    if (state.done) break;
    prevSrc = state.src;
    const png = Buffer.from(await (await ctx.request.get(state.src)).body());  // 화면에 뜬 그 이미지 그대로
    const r = await solver.ask(png);
    try {
      await page.fill("#answer", r.answer, { timeout: 2000 });
      await page.press("#answer", "Enter", { timeout: 2000 });
    } catch { continue; }  // 그 사이 시간이 끝난 경우
    log.push({ t_ms: Date.now() - t0, image: state.src.split("/").pop(), answer: r.answer, solve_ms: r.ms });
  }
  await sleep(4500);                       // 결과 화면 애니메이션까지 녹화
  const result = await page.evaluate(() => ({
    title: document.getElementById("resultTitle").textContent.replace(/\s+/g, " ").trim(),
    time: document.getElementById("rTime").textContent, streak: document.getElementById("rStreak").textContent,
  }));
  const video = await page.video().path();
  await ctx.close(); await browser.close();
  solver.proc.kill(); server.kill();

  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
  const base = path.join(OUT, `m1_claude_${MODE}_${stamp}`);
  fs.renameSync(video, base + ".webm");
  fs.rmSync(tmpVideo, { recursive: true, force: true });
  try {
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", base + ".webm", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", "30", base + ".mp4"]);
  } catch (e) { console.error("mp4 변환 실패:", e.message); }
  fs.writeFileSync(base + ".json", JSON.stringify({ result, log }, null, 1));
  console.log(JSON.stringify({ result, answered: log.length, video: base + ".mp4", log: base + ".json" }, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
