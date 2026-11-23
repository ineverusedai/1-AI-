"""사람용 로컬 웹 서버. 표준 라이브러리만 쓴다.

실행: python run.py            → http://127.0.0.1:8000 이 자동으로 열림
옵션: python run.py --port 8080 --no-browser
"""
import argparse
import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent

PAGES = {
    "/": ROOT / "common" / "web" / "hub.html",
    "/m1/": ROOT / "missions" / "m1_captcha" / "web" / "index.html",
}
# 브라우저에 내보내도 되는 폴더만 연다 (secrets/ 는 절대 안 엶)
STATIC_DIRS = {
    "/static/": ROOT / "common" / "web",
    "/data/m1/images/": ROOT / "data" / "m1" / "images",
    "/m1/": ROOT / "missions" / "m1_captcha" / "web",
}

GAMES = {}


def load_games():
    from missions.m1_captcha.game import CaptchaGame
    GAMES["m1"] = CaptchaGame()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 녹화 중 터미널을 깔끔하게

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _file(self, path: Path):
        if not path.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self._send(200, path.read_bytes(), ctype)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in PAGES:
            return self._file(PAGES[p])
        if p == "/m1":
            self.send_response(301)
            self.send_header("Location", "/m1/")
            return self.end_headers()
        for prefix, base in STATIC_DIRS.items():
            if p.startswith(prefix):
                target = (base / p[len(prefix):]).resolve()
                if base.resolve() not in target.parents:
                    return self._send(403, b"forbidden", "text/plain")
                return self._file(target)
        if p.startswith("/api/") and p.endswith("/info"):
            g = GAMES.get(p.split("/")[2])
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            return self._json(g.info(qs.get("who", ["human"])[0])) if g else self._json({"error": "no mission"}, 404)
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        parts = self.path.split("?")[0].strip("/").split("/")  # api / m1 / action
        if len(parts) != 3 or parts[0] != "api" or parts[1] not in GAMES:
            return self._json({"error": "bad path"}, 404)
        g, action = GAMES[parts[1]], parts[2]
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if action == "start":
            return self._json(g.start(str(body.get("who", "human")), str(body.get("mode", "human"))))
        if action == "answer":
            return self._json(g.answer(body.get("attempt_id", ""), str(body.get("answer", ""))))
        if action == "end":
            return self._json(g.end(body.get("attempt_id", "")))
        if action == "reset":
            return self._json(g.reset(str(body.get("who", "human"))))
        self._json({"error": "bad action"}, 404)


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["server"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=cfg["host"])
    ap.add_argument("--port", type=int, default=cfg["port"])
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    load_games()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"서버 실행 중: {url}  (끄려면 Ctrl+C)")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")


if __name__ == "__main__":
    main()
