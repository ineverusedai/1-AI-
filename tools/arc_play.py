"""미션 5 AI 플레이 도구: AI가 게임 화면(그림)을 보고 행동을 하나씩 골라 입력한다.

사람용 웹 화면과 같은 게임 파일·엔진(web_static/m5/)을 같은 방식(arcweb.py)으로 돌린다.
모든 행동은 시각과 함께 <작업 폴더>/log.jsonl 에 남고, 녹화 도구(tools/ai_play_m5.js)가 이 기록으로 리플레이 영상을 만든다.
상태는 매번 기록을 처음부터 다시 실행해 복원한다 (게임은 결정적이라 같은 결과).

사용법 (작업 폴더에서):
  python3 arc_play.py status                 지금 화면을 frame.png 로 저장하고 상태 출력
  python3 arc_play.py switch <1|2|3>         게임 바꾸기 (ls20 / ft09 / vc33)
  python3 arc_play.py act <행동> [<행동> ...]  한 번에 최대 5개. 행동: up down left right space undo reset click:X,Y (X,Y = 0~63 칸)
규칙: 30분 시간 제한, 행동 횟수 상한(config.json m5.ai_max_actions). 넘으면 더 받지 않는다.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web_static" / "m5"
sys.path.insert(0, str(WEB / "py"))
import arcweb  # noqa: E402

WORK = Path.cwd()
LOG = WORK / "log.jsonl"
GAMES = [("ls20", "Ls20"), ("ft09", "Ft09"), ("vc33", "Vc33")]
NAMES = {"up": 1, "down": 2, "left": 3, "right": 4, "space": 5, "undo": 7, "reset": 0}
COLORS = ["#FFFFFF", "#CCCCCC", "#999999", "#666666", "#333333", "#000000", "#E53AA3", "#FF7BCC",
          "#F93C31", "#1E93FF", "#88D8F1", "#FFDC00", "#FF851B", "#921231", "#4FCC30", "#A356D6"]
RGB = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in COLORS], np.uint8)
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m5"]
LIMIT_S = CFG["time_limit_min"] * 60
MAX_ACTIONS = CFG["ai_max_actions"]


def load_log():
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()] if LOG.exists() else []


def replay(log):
    """기록을 처음부터 다시 실행해 지금 상태를 만든다."""
    st = {"cur": 0, "games": []}
    for gid, cls in GAMES:
        arcweb.load(gid, cls, (WEB / "games" / f"{gid}.py").read_text(encoding="utf-8"))
        meta, frames = arcweb.step(gid, 0)
        st["games"].append(_apply(json.loads(meta), frames, {"count": 0}))
    for e in log:
        if e["kind"] == "switch":
            st["cur"] = e["game"]
        elif e["kind"] == "act":
            gid = GAMES[e["game"]][0]
            meta, frames = arcweb.step(gid, e["action"], e.get("x", -1), e.get("y", -1))
            st["games"][e["game"]] = _apply(json.loads(meta), frames, st["games"][e["game"]], e)
    return st


def _apply(meta, frames, prev, e=None):
    arr = np.frombuffer(frames, np.uint8).reshape(meta["n"], meta["h"], meta["w"]) if meta["n"] else None
    return {"levels": meta["levels"], "win": meta["win"], "state": meta["state"], "actions": meta["actions"],
            "frame": arr[-1] if arr is not None else prev.get("frame"), "count": prev.get("count", 0) + (1 if e else 0)}


def render(frame, path, scale=8):
    """64×64 칸을 8배로 키우고 8칸마다 옅은 눈금 + 좌표 숫자 (클릭 좌표 고르기용)."""
    img = Image.fromarray(RGB[frame]).resize((64 * scale, 64 * scale), Image.NEAREST)
    pad = 28
    canvas = Image.new("RGB", (64 * scale + pad, 64 * scale + pad), (20, 20, 24))
    canvas.paste(img, (pad, pad))
    d = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for k in range(0, 65, 8):
        p = pad + k * scale
        d.line([(p, pad), (p, pad + 64 * scale)], fill=(90, 90, 100), width=1)
        d.line([(pad, p), (pad + 64 * scale, p)], fill=(90, 90, 100), width=1)
        if k < 64:
            d.text((p + 2, 6), str(k), fill=(200, 200, 210), font=font)
            d.text((2, p + 2), str(k), fill=(200, 200, 210), font=font)
    canvas.save(path)


def elapsed(log):
    return (time.time() - log[0]["t"]) if log else 0.0


def report(st, log):
    g = st["games"][st["cur"]]
    render(g["frame"], WORK / "frame.png")
    used = sum(x["count"] for x in st["games"])
    out = {"current_game": f"{st['cur'] + 1}:{GAMES[st['cur']][0]}", "state": g["state"],
           "levels": f"{g['levels']}/{g['win']}", "available_actions": [k for k, v in NAMES.items() if v in g["actions"] or v == 0]
           + (["click:X,Y"] if 6 in g["actions"] else []),
           "all_games": {GAMES[i][0]: f"{x['levels']}/{x['win']} {x['state']}" for i, x in enumerate(st["games"])},
           "actions_used": f"{used}/{MAX_ACTIONS}", "elapsed_sec": round(elapsed(log)), "time_limit_sec": LIMIT_S,
           "screen": str(WORK / "frame.png")}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def append(e):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(e) + "\n")


def main(argv):
    log = load_log()
    if not log:
        append({"t": time.time(), "kind": "start"})
        log = load_log()
    if elapsed(log) > LIMIT_S:
        print("시간 제한(30분)이 끝났습니다. 더 입력할 수 없습니다.")
        return report(replay(log), log)
    cmd = argv[0] if argv else "status"
    st = replay(log)
    if cmd == "switch":
        i = int(argv[1]) - 1
        append({"t": time.time(), "kind": "switch", "game": i})
    elif cmd == "act":
        used = sum(x["count"] for x in st["games"])
        tokens = argv[1:6]
        for tok in tokens:
            if used >= MAX_ACTIONS:
                print(f"행동 횟수 상한({MAX_ACTIONS})에 도달했습니다.")
                break
            if tok.startswith("click:"):
                x, y = (int(v) for v in tok[6:].split(","))
                e = {"kind": "act", "game": st["cur"], "action": 6, "x": x, "y": y}
            elif tok in NAMES:
                e = {"kind": "act", "game": st["cur"], "action": NAMES[tok]}
            else:
                print(f"모르는 행동: {tok}")
                break
            g = st["games"][st["cur"]]
            if e["action"] != 0 and e["action"] not in g["actions"]:
                print(f"이 게임에서 쓸 수 없는 행동: {tok}")
                break
            append({"t": time.time(), **e})
            used += 1
            st = replay(load_log())
    report(replay(load_log()), load_log())


if __name__ == "__main__":
    main(sys.argv[1:])
