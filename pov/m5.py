"""미션 5 POV 영상 (ARC-AGI-3 공식 방식 AI 플레이). 실제 데이터: AI의 실제 행동 기록(ai_solutions/m5_A_official/log.jsonl)을
공식 게임 엔진으로 그대로 다시 실행한 화면, 실제 단계별 행동 수, 공식 사람 기준(게임 파일). 행동 하나에 2프레임으로 압축.
실행: python pov/m5.py <작업 폴더> <출력 mp4>"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hud import *  # noqa

D = Path(sys.argv[1]); D.mkdir(parents=True, exist_ok=True); OUT = Path(sys.argv[2])
WEB = ROOT / "web_static" / "m5"
sys.path.insert(0, str(WEB / "py"))
import arcweb
GAMES = [("ls20", "Ls20"), ("ft09", "Ft09"), ("vc33", "Vc33")]
COLORS = ["#FFFFFF", "#CCCCCC", "#999999", "#666666", "#333333", "#000000", "#E53AA3", "#FF7BCC",
          "#F93C31", "#1E93FF", "#88D8F1", "#FFDC00", "#FF851B", "#921231", "#4FCC30", "#A356D6"]
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in COLORS], np.uint8)
BASE_ACT = {g: json.loads((WEB / "games" / f"{g}.json").read_text())["baseline_actions"] for g, _ in GAMES}
ICON = {0: "RESET", 1: "UP", 2: "DOWN", 3: "LEFT", 4: "RIGHT", 5: "SPACE", 6: "CLICK", 7: "UNDO"}
ARW = {1: "^", 2: "v", 3: "<", 4: ">"}

# ---------- 기록 다시 실행 ----------
log = [json.loads(l) for l in (ROOT / "ai_solutions/m5_A_official/log.jsonl").read_text().splitlines() if l.strip()]
t0 = log[0]["t"]
st = []
for gid, cls in GAMES:
    arcweb.load(gid, cls, (WEB / "games" / f"{gid}.py").read_text())
    m, fr = arcweb.step(gid, 0); m = json.loads(m)
    st.append({"frame": np.frombuffer(fr, np.uint8).reshape(m["n"], 64, 64)[-1], "levels": 0, "win": m["win"], "lvl_n": 0, "per": [], "state": m["state"]})
steps = []  # (cur, event, prev_frame, frame, levels snapshot, total, real_t, level_done)
cur = 0; total = 0
for e in log:
    if e["kind"] == "switch":
        cur = e["game"]; steps.append(dict(kind="switch", cur=cur, t=e["t"] - t0)); continue
    if e["kind"] != "act":
        continue
    g = st[e["game"]]; gid = GAMES[e["game"]][0]
    m, fr = arcweb.step(gid, e["action"], e.get("x", -1), e.get("y", -1)); m = json.loads(m)
    prev = g["frame"]
    if m["n"]:
        g["frame"] = np.frombuffer(fr, np.uint8).reshape(m["n"], 64, 64)[-1]
    g["lvl_n"] += 1; total += 1; done = None
    if m["levels"] > g["levels"]:
        done = (e["game"], g["levels"], g["lvl_n"], BASE_ACT[gid][g["levels"]]); g["per"].append(g["lvl_n"]); g["lvl_n"] = 0
    g["levels"] = m["levels"]; g["state"] = m["state"]
    steps.append(dict(kind="act", cur=e["game"], a=e["action"], x=e.get("x", -1), y=e.get("y", -1), prev=prev, frame=g["frame"].copy(),
                      levels=[s["levels"] for s in st], lvl_n=g["lvl_n"], total=total, t=e["t"] - t0, done=done,
                      wins=[s["state"] == "WIN" for s in st]))
assert [s["levels"] for s in st] == [7, 6, 7], [s["levels"] for s in st]
print("다시 실행 확인: 20/20, 행동", total)

# ---------- 시간표: 행동 2프레임, 단계 통과 0.5초 멈춤 ----------
timeline = []  # (step 번호, 그 안의 프레임 번호)
for i, s in enumerate(steps):
    n = 2 if s["kind"] == "act" else 6
    if s["kind"] == "act" and s["done"]:
        n = 30
    timeline += [(i, k) for k in range(n)]
INTRO, OUTRO = 60, 330
N = INTRO + len(timeline) + OUTRO
base = make_base()
GX, GY, GS = 120, 200, 832; CELL = GS // 64
done_list = []
wr = Writer(OUT)
last = {"cur": 0, "frame": st[0]["frame"]}
frames0 = []
for gid, cls in GAMES:  # 첫 화면
    arcweb.load(gid, cls, (WEB / "games" / f"{gid}.py").read_text()); m, fr = arcweb.step(gid, 0); m = json.loads(m)
    frames0.append(np.frombuffer(fr, np.uint8).reshape(m["n"], 64, 64)[-1])
shown = list(frames0); levels = [0, 0, 0]; wins = [False] * 3; total = 0; lvl_n = 0; real_t = 0.0; cur = 0
for f in range(N):
    im, dr = chrome(base, f, "M5 // ARC-AGI-3  OFFICIAL RULES", "NO INSTRUCTIONS  64x64  LEVEL BUDGET = HUMAN BASELINE x5")
    ev = None
    if INTRO <= f < INTRO + len(timeline):
        i, k = timeline[f - INTRO]; s = steps[i]
        cur = s["cur"]; real_t = s["t"]
        if s["kind"] == "act":
            shown[cur] = s["frame"]; levels = s["levels"]; wins = s["wins"]; total = s["total"]; lvl_n = s["lvl_n"]
            ev = (s, k)
            if s["done"] and k == 0:
                done_list.append(s["done"])
    # 게임 화면
    al = ease((f - 20) / 30)
    g = Image.fromarray(PAL[shown[cur]]).resize((GS, GS), Image.NEAREST)
    im.paste(Image.blend(Image.new("RGB", g.size, BG), g, al), (GX, GY))
    bracket(dr, GX - 10, GY - 10, GX + GS + 10, GY + GS + 10)
    dr.text((GX, GY - 40), f"{GAMES[cur][0].upper()}   VIEW 64x64", font=F16, fill=CY)
    if ev:
        s, k = ev
        if s["kind"] == "act":
            ch = np.argwhere(s["prev"] != s["frame"])  # 바뀐 칸
            if len(ch) and k < 2:
                for yy, xx in ch[:400]:
                    dr.rectangle([GX + xx * CELL, GY + yy * CELL, GX + xx * CELL + CELL - 1, GY + yy * CELL + CELL - 1], outline=AMB)
            if s["a"] == 6 and s["x"] >= 0:
                cx, cy = GX + s["x"] * CELL + CELL // 2, GY + s["y"] * CELL + CELL // 2
                dr.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=WHT, width=3)
                dr.line([(cx - 28, cy), (cx + 28, cy)], fill=WHT); dr.line([(cx, cy - 28), (cx, cy + 28)], fill=WHT)
            dr.text((GX + GS - 220, GY - 40), ICON[s["a"]] + (f" {s['x']},{s['y']}" if s["a"] == 6 else ""), font=F16, fill=AMB)
            if s["a"] in ARW:
                dr.text((GX + GS + 40, GY), ARW[s["a"]], font=F96, fill=fade(AMB, 0.8))
            if s["done"]:
                gi, lv, n, hb = s["done"]
                fl = 1 - k / 30
                dr.rectangle([GX - 4, GY - 4, GX + GS + 4, GY + GS + 4], outline=fade(GRN, fl), width=6)
                dr.text((GX + 40, GY + GS // 2 - 60), f"L{lv + 1}  CLEAR", font=F96, fill=fade(GRN, fl))
                dr.text((GX + 40, GY + GS // 2 + 70), f"AI {n}   HUMAN {hb}", font=F44, fill=fade(WHT, fl))
    # 오른쪽 HUD: 게임별 단계
    RX = 1080
    for j, (gid, _) in enumerate(GAMES):
        y = 200 + j * 90; wn = BASE_ACT[gid]; nl = len(wn); on = j == cur
        dr.text((RX, y), gid.upper(), font=F28, fill=CY if on else MID)
        for L in range(nl):
            x0 = RX + 150 + L * 64
            col = GRN if L < levels[j] else ((40, 60, 70) if not on or L != levels[j] else AMB)
            dr.rectangle([x0, y + 6, x0 + 54, y + 30], fill=col)
        if wins[j]:
            dr.text((RX + 150 + nl * 64 + 10, y), "WIN", font=F20, fill=GRN)
    # 지금 단계: 사람 기준과 행동 상한
    gid = GAMES[cur][0]
    if not wins[cur]:
        hb = BASE_ACT[gid][min(levels[cur], len(BASE_ACT[gid]) - 1)]
        y = 500
        dr.text((RX, y), f"LEVEL {levels[cur] + 1}  ACTIONS", font=F16, fill=CY)
        dr.text((RX, y + 24), f"{lvl_n:3d}", font=F64, fill=WHT)
        sc = 700 / (5 * hb)
        dr.rectangle([RX, y + 110, RX + 700, y + 126], outline=DIM)
        dr.rectangle([RX, y + 110, RX + int(min(700, lvl_n * sc)), y + 126], fill=AMB if lvl_n > hb else CY)
        hx = RX + int(hb * sc); dr.line([(hx, y + 100), (hx, y + 136)], fill=WHT, width=2)
        dr.text((hx - 40, y + 142), f"HUMAN {hb}", font=F12, fill=WHT)
        dr.text((RX + 600, y + 142), f"x5 {5 * hb}", font=F12, fill=RED)
    # 총계
    y = 720
    dr.text((RX, y), "TOTAL ACTIONS", font=F12, fill=DIM); dr.text((RX, y + 18), f"{total:3d}", font=F44, fill=WHT)
    dr.text((RX + 260, y), "LEVELS", font=F12, fill=DIM); dr.text((RX + 260, y + 18), f"{sum(levels):2d}/20", font=F44, fill=GRN)
    rt = int(real_t)
    dr.text((RX + 520, y), "REAL TIME", font=F12, fill=DIM); dr.text((RX + 520, y + 18), f"{rt // 60:02d}:{rt % 60:02d}", font=F44, fill=AMB)
    # 단계별 효율 막대 (깬 순서대로)
    y = 860
    dr.text((RX, y), "PER LEVEL  AI vs HUMAN", font=F12, fill=CY)
    for k2, (gi, lv, n, hb) in enumerate(done_list):
        x0 = RX + k2 * 36; sc = 160 / 200
        dr.rectangle([x0, y + 200 - int(min(200, hb) * sc), x0 + 14, y + 200], fill=(60, 70, 80))
        dr.rectangle([x0 + 16, y + 200 - int(min(200, n) * sc), x0 + 30, y + 200], fill=CY if n <= hb else AMB)
    # 마무리 요약
    if f >= INTRO + len(timeline):
        t = (f - INTRO - len(timeline)) / 120; a2 = ease(t)
        dr.rectangle([GX - 20, GY - 20, GX + GS + 20, GY + GS + 20], fill=BG)
        dr.text((GX + 20, GY + 80), "20/20", font=F96, fill=fade(GRN, a2))
        dr.text((GX + 20, GY + 230), "AI  721 ACTIONS", font=F44, fill=fade(WHT, a2))
        dr.text((GX + 20, GY + 300), f"HUMAN BASELINE  {sum(sum(v) for v in BASE_ACT.values()):,}", font=F44, fill=fade(MID, a2))
        dr.text((GX + 20, GY + 400), "REAL 45:41", font=F44, fill=fade(AMB, a2))
        dr.text((GX + 20, GY + 470), "@30:00  13/20", font=F28, fill=fade(RED, ease(t - 0.5)))
    im = fade_out(im, f, N - 60, N)
    wr.write(im)
wr.close()
print("완료", OUT, N / FPS, "초")
