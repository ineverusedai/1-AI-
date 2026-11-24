"""AI 테스트용 문제 파일만 ai_test/<미션>/ 으로 복사한다.

복사하는 것: 문제 이미지, 문제 목록(번호·파일 이름), 규칙 설명
복사하지 않는 것: 정답 해시, 시드, 비밀 키, 생성 코드

실행: python -m tools.export_ai_test m1   (또는 m2, m3, m4)
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


M2_README = """# 미션 2: 착시 캡차 (AI 테스트)

사람이 보는 안내와 같은 수준의 설명만 준다: **착시 캡차 — 눈을 가늘게 뜨면 보이는 글자.**
그림마다 선택지 4개가 있고, 그림 속에 숨은 글자를 고르는 문제다. (사람 화면에도 선택지 4개만 보인다.)

- `images/q001.jpg` ~ : 원본 그림 ({width}×{height}, 사람이 보는 것과 같은 파일)
- `small/q001.png` ~ : 같은 그림을 흐리게 한 뒤 {sw}×{sh}로 줄인 것
- `questions.json` : 문제 번호, 두 그림의 파일 이름, 선택지 4개 (화면에 보이는 순서 그대로)

## 기록 방식 (그림 두 가지 × 푸는 방식 두 가지)
- `A-orig` : 원본 그림을 직접 보고 고르기 (코드 없이)
- `A-small` : 줄인 그림을 직접 보고 고르기 (코드 없이)
- `B-orig` : 원본 그림을 코드로 분석해서 고르기
- `B-small` : 줄인 그림을 코드로 분석해서 고르기

## 사람과 같은 규칙
{limit}초 안에 {target}문제 연속 정답이면 성공. 틀리면 연속 카운트가 0이 된다.
문제는 반드시 **1번부터 번호 순서대로** 푼다. 틀렸다는 알림은 없다(채점은 나중에 따로 한다).

## 제출
`python ../submit.py m2 <방식> start` → 문제마다 `python ../submit.py m2 <방식> answer <번호> <선택지 번호 1~4>`
→ 끝나면 `python ../submit.py m2 <방식> end`. 예: `python ../submit.py m2 A-orig answer 1 3`
"""


def export_m2() -> None:
    import cv2

    src = ROOT / "data" / "m2"
    dst = AI / "m2"
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m2"]
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "images").mkdir(parents=True)
    (dst / "small").mkdir()
    sw, sh = cfg["width"] // 6, cfg["height"] // 6
    questions = []
    for q in manifest["questions"]:
        shutil.copy2(src / "images" / q["file"], dst / "images" / q["file"])
        img = cv2.imread(str(src / "images" / q["file"]))
        small = cv2.resize(cv2.GaussianBlur(img, (0, 0), 6), (sw, sh), interpolation=cv2.INTER_AREA)
        name = q["file"].rsplit(".", 1)[0] + ".png"
        cv2.imwrite(str(dst / "small" / name), small)
        # 해시는 빼고 번호, 파일 이름, 선택지만
        questions.append({"q": q["q"], "file": "images/" + q["file"], "small": "small/" + name, "choices": q["choices"]})
    (dst / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=1), encoding="utf-8")
    (dst / "README.md").write_text(M2_README.format(
        width=cfg["width"], height=cfg["height"], sw=sw, sh=sh,
        limit=cfg["time_limit_sec"], target=cfg["streak_target"]), encoding="utf-8")
    print(f"ai_test/m2: 문제 {len(questions)}개 복사 + 줄인 그림 (정답 해시·시드·키 없음)")


M3_README = """# 미션 3: 소리 착시 캡차 (AI 테스트, 방식 B만)

사람이 보는 안내와 같은 수준: **원본 음성을 듣고, 사인파로 바꾼 소리 4개 중 같은 문장을 고른다.**
- `qNN/ref.wav` : 깨끗한 원본 음성 (한국어 문장 하나)
- `qNN/opt1.wav` ~ `opt4.wav` : 사인파 음성 4개 (화면의 소리 1~4)
- `questions.json` : 문제 번호와 폴더

## 사람과 같은 규칙
한 판에 {per}문제(1~{per}번), **하나라도 틀리면 실패**. 시간 제한은 없고 걸린 시간을 기록한다. 번호 순서대로 푼다.
AI는 소리를 직접 들을 수 없으므로 코드로 분석해서 고른다 (방식 `B`).

## 제출
`python ../submit.py m3 B start` → 문제마다 `python ../submit.py m3 B answer <번호> <1~4>` → `python ../submit.py m3 B end`
"""


def export_m3() -> None:
    src = ROOT / "data" / "m3"
    dst = AI / "m3"
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m3"]
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    questions = []
    for q in manifest["questions"]:
        shutil.copytree(src / "audio" / q["dir"], dst / q["dir"])
        questions.append({"q": q["q"], "dir": q["dir"], "ref": f"{q['dir']}/ref.wav",
                          "options": [f"{q['dir']}/opt{n}.wav" for n in range(1, 5)]})
    (dst / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=1), encoding="utf-8")
    (dst / "README.md").write_text(M3_README.format(per=cfg["questions_per_round"]), encoding="utf-8")
    print(f"ai_test/m3: 문제 {len(questions)}개 복사 (정답 해시·시드·키·문장 목록 없음)")


M4_README = """# 미션 4: 움직여야 보이는 캡차 (AI 테스트)

사람이 보는 것과 같은 영상: 점이 흩뿌려진 3초짜리 영상(반복 재생)과 선택지 6개(A~F). 영상 속 글자와 같은 선택지를 고른다.
- `videos/qNN.mp4` : 사람 화면과 같은 영상 (488×488, 30fps, 90프레임)
- `frames/qNN_still.png` : 영상의 첫 프레임 1장
- `frames/qNN_seq/f00.png` ~ `f{last:02d}.png` : 영상의 처음 {nseq}프레임 (연속)
- `questions.json` : 번호, 파일, 선택지 6개 (화면 순서 그대로, A~F)

## 기록 방식
- `A-still` : 정지 프레임 1장만 직접 보고 고르기 (코드 없이)
- `A-frames` : 연속 프레임 여러 장을 직접 보고 고르기 (코드 없이)
- `B` : 코드로 영상(움직임)을 분석해서 고르기

## 사람과 같은 규칙
{limit}초 안에 {per}문제(1~{per}번) 모두 정답이면 성공, 하나라도 틀리면 실패. 번호 순서대로 푼다.

## 제출
`python ../submit.py m4 <방식> start` → `python ../submit.py m4 <방식> answer <번호> <A~F>` → `python ../submit.py m4 <방식> end`
"""


def export_m4() -> None:
    import subprocess

    src = ROOT / "data" / "m4"
    dst = AI / "m4"
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m4"]
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "videos").mkdir(parents=True)
    (dst / "frames").mkdir()
    nseq = 8
    questions = []
    for q in manifest["questions"]:
        stem = q["file"].rsplit(".", 1)[0]
        shutil.copy2(src / "videos" / q["file"], dst / "videos" / q["file"])
        seq = dst / "frames" / f"{stem}_seq"
        seq.mkdir()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src / "videos" / q["file"]), "-frames:v", str(nseq),
                        str(seq / "f%02d.png"), "-start_number", "0"], check=True)
        files = sorted(seq.glob("f*.png"))
        for i, f in enumerate(files):  # ffmpeg 는 1부터 번호를 매기므로 0부터로 바꿈
            f.rename(seq / f"f{i:02d}.png.tmp")
        for f in sorted(seq.glob("*.tmp")):
            f.rename(seq / f.name[:-4])
        shutil.copy2(seq / "f00.png", dst / "frames" / f"{stem}_still.png")
        questions.append({"q": q["q"], "video": "videos/" + q["file"], "still": f"frames/{stem}_still.png",
                          "seq": [f"frames/{stem}_seq/f{i:02d}.png" for i in range(nseq)], "options": q["options"]})
    (dst / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=1), encoding="utf-8")
    (dst / "README.md").write_text(M4_README.format(last=nseq - 1, nseq=nseq, limit=cfg["time_limit_sec"],
                                                    per=cfg["questions_per_round"]), encoding="utf-8")
    print(f"ai_test/m4: 문제 {len(questions)}개 복사 + 정지·연속 프레임 (정답 해시·시드·키 없음)")


EXPORTERS = {"m1": export_m1, "m2": export_m2, "m3": export_m3, "m4": export_m4}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in EXPORTERS:
        raise SystemExit(f"사용법: python -m tools.export_ai_test <{'|'.join(EXPORTERS)}>")
    EXPORTERS[sys.argv[1]]()
