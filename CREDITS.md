# CREDITS

영상 설명란에 붙여 넣기용. 미션을 추가할 때마다 갱신한다.

## 미션 1: 글자 캡차
- **captcha** 0.7.1 — lepture/captcha, BSD-3-Clause — https://github.com/lepture/captcha
  - 내장 글꼴 **DroidSansMono** — Apache License 2.0 (captcha 패키지에 포함)
  - 시드 고정을 위해 생성 중에만 라이브러리 내부 난수(`secrets`)를 시드 난수로 바꿔 사용 (라이브러리 파일 자체는 수정하지 않음)
- **Pillow** — HPND (MIT-CMU) 라이선스 — https://python-pillow.org

## 공통
- 로컬 서버·채점·기록: Python 표준 라이브러리 (`http.server`, `hmac`, `hashlib`, `csv`)
- 정답 저장: HMAC-SHA256 해시만 저장 (평문 정답 없음)
- 코드: 이 프로젝트용으로 Claude Code가 작성
