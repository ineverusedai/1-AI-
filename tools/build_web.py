"""정적 웹 버전(docs/) 만들기. GitHub Pages나 파일 더블클릭으로 열 수 있다.

실행: python -m tools.build_web

docs/ 구조
  index.html, style.css, hmac.js, records.js
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


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    shutil.copy2(ROOT / "common" / "web" / "style.css", OUT / "style.css")
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
