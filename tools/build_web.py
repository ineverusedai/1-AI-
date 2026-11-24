"""정적 웹 버전(docs/)과 Python 서버용 화면 만들기. docs/ 는 GitHub Pages나 파일 더블클릭으로 열 수 있다.

실행: python -m tools.build_web

docs/ 구조
  index.html, style.css, fonts/, hmac.js, records.js
  m1/index.html, m1/data.js (규칙 + 정답 해시 + 채점 키), m1/images/

주의: 정적 페이지는 브라우저 안에서 채점해야 해서 채점 키가 m1/data.js 에 들어간다.
      평문 정답은 여전히 없지만, 키가 있으면 후보를 대입해 답을 알아낼 수는 있다.
      AI 테스트는 ai_test/ 만 보고 하므로 docs/ 는 AI에게 주지 않는다.
"""
import json
import shutil
from pathlib import Path

from common.answer_hash import load_key

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web_static"
OUT = ROOT / "docs"


STATIC_SCRIPTS = """<script src="../hmac.js"></script>
<script src="../records.js"></script>
<script src="data.js"></script>
<script src="ui.js"></script>
<script src="engine.js"></script>"""


def build_server_page() -> None:
    """Python 서버(run.py)용 미션 1 화면을 같은 원본에서 만든다. 채점 스크립트만 서버용으로 바꿈."""
    web = ROOT / "missions" / "m1_captcha" / "web"
    html = (SRC / "m1" / "index.html").read_text(encoding="utf-8")
    assert STATIC_SCRIPTS in html, "web_static/m1/index.html 의 script 태그가 예상과 다릅니다"
    html = html.replace('href="../style.css"', 'href="/static/style.css"')
    html = html.replace(STATIC_SCRIPTS, '<script src="/m1/ui.js"></script>\n<script src="/m1/engine.js"></script>')
    (web / "index.html").write_text(html, encoding="utf-8")
    shutil.copy2(SRC / "m1" / "ui.js", web / "ui.js")


def main() -> None:
    build_server_page()
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    shutil.copy2(ROOT / "common" / "web" / "style.css", OUT / "style.css")
    shutil.copytree(ROOT / "common" / "web" / "fonts", OUT / "fonts")
    (OUT / ".nojekyll").write_text("")

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m1"]
    manifest = json.loads((ROOT / "data" / "m1" / "manifest.json").read_text(encoding="utf-8"))
    shutil.copytree(ROOT / "data" / "m1" / "images", OUT / "m1" / "images")
    data = {
        "title": cfg["title"],
        "time_limit_sec": cfg["time_limit_sec"],
        "streak_target": cfg["streak_target"],
        "answer_rule": manifest["answer_rule"],
        "key": load_key().hex(),
        "questions": [{"file": q["file"], "hash": q["hash"]} for q in manifest["questions"]],
    }
    (OUT / "m1" / "data.js").write_text(
        "window.M1_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"docs/ 생성 완료 (미션 1: 문제 {len(data['questions'])}개)")


if __name__ == "__main__":
    main()
