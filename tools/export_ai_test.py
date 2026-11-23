"""AI 테스트용 문제 파일만 ai_test/<미션>/ 으로 복사한다.

복사하는 것: 문제 이미지, 문제 목록(번호·파일 이름), 규칙 설명
복사하지 않는 것: 정답 해시, 시드, 비밀 키, 생성 코드

실행: python -m tools.export_ai_test m1
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai_test"

M1_README = """# 미션 1: 글자 캡차 (AI 테스트)

`images/q001.png` ~ `images/q{last:03d}.png` 에 찌그러진 글자 이미지가 있다. 각 이미지의 글자를 그대로 적는 문제다.

- 글자 수: {length}자
- 쓰이는 글자: 대문자 A-Z, 숫자 0-9. 소문자는 없다 (대소문자 구분 없이 채점).
- 문제 3개 중 1개꼴로 헷갈리는 글자가 하나 섞여 있다: 0(숫자 영) / O(대문자 오) / 1(숫자 일) / I(대문자 아이)
- 이미지는 Python `captcha` 라이브러리 0.7.1(lepture/captcha, `ImageCaptcha(width={width}, height={height})`, 기본 글꼴)로 만들었다.

## 사람과 같은 규칙
{limit}초 안에 {target}문제 연속 정답이면 성공. 틀리면 연속 카운트가 0이 된다.
문제는 반드시 **1번부터 번호 순서대로** 푼다. 틀렸다는 알림은 없다(채점은 나중에 따로 한다).

## 기록되는 것
1. 1~10번을 푸는 데 걸린 시간과 정답 수
2. 시작 후 {limit}초 안에 맞힌 문제 수 (= "1분 동안 최대 몇 문제")
3. 위 규칙대로 했을 때 성공 여부

## 제출
`python ../submit.py m1 <A 또는 B> start` 로 시작 → 문제마다 `python ../submit.py m1 <A 또는 B> answer <번호> <답>`
→ 끝나면 `python ../submit.py m1 <A 또는 B> end`. 할 수 있는 만큼 계속 풀어도 된다(최대 {last}번).
"""


def export_m1() -> None:
    src = ROOT / "data" / "m1"
    dst = AI / "m1"
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m1"]
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "images").mkdir(parents=True)
    for q in manifest["questions"]:
        shutil.copy2(src / "images" / q["file"], dst / "images" / q["file"])
    # 해시는 빼고 번호와 파일 이름만
    questions = [{"q": q["q"], "file": "images/" + q["file"]} for q in manifest["questions"]]
    (dst / "questions.json").write_text(json.dumps(questions, indent=1), encoding="utf-8")
    (dst / "README.md").write_text(M1_README.format(
        last=len(questions), length=cfg["length"], width=cfg["width"], height=cfg["height"],
        limit=cfg["time_limit_sec"], target=cfg["streak_target"]), encoding="utf-8")
    print(f"ai_test/m1: 문제 {len(questions)}개 복사 (정답 해시·시드·키 없음)")


EXPORTERS = {"m1": export_m1}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in EXPORTERS:
        raise SystemExit(f"사용법: python -m tools.export_ai_test <{'|'.join(EXPORTERS)}>")
    EXPORTERS[sys.argv[1]]()
