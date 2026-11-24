# CREDITS

영상 설명란에 붙여 넣기용. 미션을 추가할 때마다 갱신한다.

## 미션 1: 글자 캡차
- **captcha** 0.7.1 — lepture/captcha, BSD-3-Clause — https://github.com/lepture/captcha
  - 내장 글꼴 **DroidSansMono** — Apache License 2.0 (captcha 패키지에 포함)
  - 시드 고정을 위해 생성 중에만 라이브러리 내부 난수(`secrets`)를 시드 난수로 바꿔 사용 (라이브러리 파일 자체는 수정하지 않음)
- **Pillow** — HPND (MIT-CMU) 라이선스 — https://python-pillow.org

## 미션 2: 착시 캡차
- 방식 참고: Ding 외, **"IllusionCAPTCHA: A CAPTCHA based on Visual Illusion"**, arXiv:2502.05461 (2025) — https://arxiv.org/abs/2502.05461
  - 따른 것: 숨은 내용은 짧고 익숙한 낱말, 선택지 4개 중 하나는 그림을 만들 때 쓴 장면 문구(함정), 후보 여러 장 중 숨은 내용이 가장 덜 드러나는 그림을 고름
  - 다른 것: 논문은 확산 모델(ControlNet)로 그림을 만들지만 여기서는 아래 하이브리드 이미지로 코드만으로 만듦. 논문의 나머지 두 선택지(장면을 길게 설명한 문장) 대신 정답과 첫 글자가 같은 낱말 2개를 넣음
- 하이브리드 이미지: Oliva, Torralba, Schyns, **"Hybrid Images"**, ACM SIGGRAPH 2006 (ACM Transactions on Graphics 25(3))
- **OpenCV** (opencv-python-headless) — Apache License 2.0 — https://opencv.org
- **NumPy** — BSD-3-Clause — https://numpy.org
- 배경 그림(나뭇잎·숲·풀밭)은 OpenCV 도형 그리기로 직접 생성, 숨은 글자는 Pretendard 글꼴로 그림

## 미션 3: 소리 착시 캡차
- 방식 참고: **"Robust CAPTCHA Using Audio Illusions in the Era of Large Language Models: from Evaluation to Advances"** (IllusionAudio), arXiv:2601.08516 (2026) — https://arxiv.org/abs/2601.08516
  - 따른 것: 사인파 음성 착시, 깨끗한 원본 음성을 먼저 들려줌, 사인파 변환 뒤 되돌릴 수 없는 무작위 다운샘플링(논문이 값을 공개하지 않아 '분석 프레임 무작위 붙잡기'로 구현)
  - 다른 것: 문제 방식(원본 듣고 4개 중 고르기, 5문제 하나라도 틀리면 실패)은 이 프로젝트 사양
- 사인파 음성 변환: **johnhw/sinewave_speech** — John Williamson, MIT License (LPC 부분 Cournapeau David, MIT) — https://github.com/johnhw/sinewave_speech
  (`third_party/sinewave_speech/`에 수정 없이 넣고 함수만 불러 씀)
- 사인파 음성: Remez, Rubin, Pisoni, Carrell, **"Speech perception without traditional speech cues"**, Science 212 (1981)
- **SciPy** — BSD-3-Clause — https://scipy.org
- 원본 음성: 사용자 컴퓨터 내장 한국어 TTS (맥 Yuna / 윈도우 한국어 음성). 임시 음성은 **eSpeak NG** (GPL-3.0, 프로그램을 실행해 소리만 만듦)

## 미션 4: 움직여야 보이는 캡차
- **MVCAP** (Motion Vision CAPTCHA) — 공식 코드 zeyu1998/MVCAP, MIT License — https://github.com/zeyu1998/MVCAP
  - 논문: **"Invisible in Space, Visible in Time: Motion Vision CAPTCHA against GUI Agents"**, ACM Multimedia 2026 (arXiv:2609.27461) — https://doi.org/10.1145/3767308.3835234
  - L1 생성기(`third_party/mvcap/MVCAP_code/L1`)를 수정 없이 불러 씀. 기본값 그대로: 488×488, 30fps, 3초, 4글자(헷갈리는 글자 뺀 32자), 정답 + 오답 5개 = 6지선다(A~F로 섞음)
  - L2·L3는 ShapeNet·BABEL 등 서드파티 자료 약관 때문에 쓰지 않음
  - 글꼴: DejaVu Sans Bold (공식 코드가 찾는 글꼴 중 리눅스에 있는 것)
- **OpenCV**, **NumPy**, **Pillow**, **FFmpeg**(libx264) — 공식 코드가 쓰는 라이브러리

## 미션 5: ARC-AGI-3
- **ARC-AGI-3** — ARC Prize Foundation. 공식 Toolkit **arc-agi** 0.9.10, 엔진 **arcengine** 0.9.3, 게임 LS20·FT09·VC33 소스 — 모두 MIT License — https://arcprize.org
- **Pyodide** 0.27.7 (브라우저 안 파이썬) — Mozilla Public License 2.0 — https://pyodide.org
- Pyodide 배포판의 **NumPy** (BSD-3), **pydantic**·**pydantic-core** (MIT), **typing-extensions** (PSF), **annotated-types** (MIT)
- 색상표: 공식 toolkit 의 COLOR_MAP 그대로

## 공통
- 로컬 서버·채점·기록: Python 표준 라이브러리 (`http.server`, `hmac`, `hashlib`, `csv`)
- 브라우저 버전 채점: SHA-256/HMAC을 자바스크립트로 직접 구현 (외부 라이브러리 없음)
- 정답 저장: HMAC-SHA256 해시만 저장 (평문 정답 없음)
- 코드: 이 프로젝트용으로 Claude Code가 작성

## 화면 글꼴 (common/web/fonts/, 사이트에 직접 포함)
- **Pretendard** v1.3.9 (가변 글꼴) — Kil Hyung-jin, SIL Open Font License 1.1 — https://github.com/orioncactus/pretendard
- **JetBrains Mono** (가변 글꼴, 라틴 부분, @fontsource-variable/jetbrains-mono 5.1.1) — JetBrains, SIL Open Font License 1.1 — https://github.com/JetBrains/JetBrainsMono
- 맥·윈도우·녹화 영상에서 똑같은 글씨체가 나오도록 외부 글꼴 사이트 대신 파일을 직접 넣었다.
