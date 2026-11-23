# 24시간 안에 인간임을 인증하기

사람(로컬 웹 페이지)과 Claude(AI 테스트)가 같은 문제를 풀고 결과를 비교하는 프로젝트.

## 설치 (처음 한 번)
Python 3.10 이상 필요.

macOS / Linux
```bash
cd human-verify-24h
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell)
```powershell
cd human-verify-24h
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 실행
```bash
python run.py
```
브라우저에서 http://127.0.0.1:8000 이 열린다. 미션을 고르고 `Enter`로 시작.
끄려면 터미널에서 `Ctrl+C`.

## 미션 1: 글자 캡차
- 60초 안에 10문제 연속 정답이면 성공. 틀리면 연속 카운트 0, 시간은 계속 흐름.
- 다시 도전하면 이미 본 문제는 건너뛰고 다음 번호부터 나온다. 문제 #1부터 다시 하려면 시작 화면의 **처음 문제(#1)부터** 버튼.
- 규칙 숫자는 `config.json` 의 `m1` 에서 바꿀 수 있다.
- 문제는 이미 `data/m1/` 에 만들어져 있다. 다시 만들 때만: `python -m missions.m1_captcha.generate`

## 결과 파일
- `results/answers.csv` — 답 하나당 한 줄: 누가(`human`/`claude`), 미션, 방식, 도전 번호, 문제 번호, 제출한 답, 정답 여부, 그 문제에 걸린 시간(ms), 시작부터 누적 시간(ms)
- `results/summary.csv` — 도전 하나당 한 줄: 성공 여부, 맞힌 수, 최고 연속, 1~10번 정답 수·시간, 제한 시간 안 정답 수
- 연습한 기록을 지우고 싶으면 `results/` 안의 `answers.csv`, `summary.csv`, `.state_m1.json` 을 지우면 된다.

## AI 테스트 공정성
- 정답은 평문으로 저장하지 않는다. `data/*/manifest.json` 에는 **비밀 키로 만든 HMAC 해시**만 있다.
  (그냥 해시면 4지선다처럼 후보가 적은 문제는 후보를 다 대입해 정답을 알아낼 수 있어서 키를 섞었다.)
- 비밀 키와 시드는 `secrets/` 에만 있다. **영상에 이 폴더 내용이 나오지 않게 조심.**
- `ai_test/` 에는 문제 파일과 규칙만 복사된다 (`python -m tools.export_ai_test m1`).
- Claude는 별도 서브에이전트가 `ai_test/` 만 보고 풀고, 답과 시각을 `ai_test/_log/` 에 남긴다.
  채점은 `python -m tools.grade_ai m1 A` 가 해시를 비교해서 `results/` 에 기록한다.

## 폴더
```
run.py                 로컬 서버 (표준 라이브러리만 사용)
config.json            미션별 규칙
secrets/               시드, HMAC 키 (AI 테스트에 복사 안 함)
common/                해시·결과 기록·공통 화면
missions/m1_captcha/   문제 생성기, 게임 로직, 화면
data/m1/               생성된 문제 이미지 + 해시 목록
ai_test/               AI용 문제지 + 제출기
tools/                 AI 문제지 내보내기, AI 채점
results/               CSV 결과
audio/originals/       미션 3 원본 음성 (나중에)
```
