# CREDITS

영상 설명란에 붙여 넣기용. 미션을 추가할 때마다 갱신한다.

## 미션 1: 글자 캡차
- **captcha** 0.7.1 — lepture/captcha, BSD-3-Clause — https://github.com/lepture/captcha
  - 내장 글꼴 **DroidSansMono** — Apache License 2.0 (captcha 패키지에 포함)
  - 시드 고정을 위해 생성 중에만 라이브러리 내부 난수(`secrets`)를 시드 난수로 바꿔 사용 (라이브러리 파일 자체는 수정하지 않음)
- **Pillow** — HPND (MIT-CMU) 라이선스 — https://python-pillow.org

## 공통
- 로컬 서버·채점·기록: Python 표준 라이브러리 (`http.server`, `hmac`, `hashlib`, `csv`)
- 브라우저 버전 채점: SHA-256/HMAC을 자바스크립트로 직접 구현 (외부 라이브러리 없음)
- 정답 저장: HMAC-SHA256 해시만 저장 (평문 정답 없음)
- 코드: 이 프로젝트용으로 Claude Code가 작성

## 화면 글꼴 (common/web/fonts/, 사이트에 직접 포함)
- **Pretendard** v1.3.9 (가변 글꼴) — Kil Hyung-jin, SIL Open Font License 1.1 — https://github.com/orioncactus/pretendard
- **JetBrains Mono** (가변 글꼴, 라틴 부분, @fontsource-variable/jetbrains-mono 5.1.1) — JetBrains, SIL Open Font License 1.1 — https://github.com/JetBrains/JetBrainsMono
- 맥·윈도우·녹화 영상에서 똑같은 글씨체가 나오도록 외부 글꼴 사이트 대신 파일을 직접 넣었다.
