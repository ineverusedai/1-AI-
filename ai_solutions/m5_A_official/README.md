# 과제: ARC-AGI-3 게임 3개 직접 플레이 (미션 5, 공식 방식)

처음 보는 퍼즐 게임 3개(1: ls20, 2: ft09, 3: vc33)를 **화면을 보고 행동을 골라** 플레이한다. 규칙 설명은 없다 (사람도 같음).
각 게임은 여러 단계(level)로 되어 있고, 단계를 깨면 다음 단계로 넘어간다. 목표: 모든 게임의 모든 단계를 깨기. 적은 행동으로 깰수록 좋다.

## 공식 방식 규칙
- 시간 제한 없음. 대신 **단계마다 행동 상한** (사람 기준 행동 수 × 5). 지금 단계에 남은 행동 수는 status 의 `level_actions_left`.
  상한을 넘으면 그 게임은 끝 (BUDGET_OUT). 다른 게임은 계속할 수 있다.
- 행동으로 세는 것: 게임 상태를 바꾸는 입력(reset 포함). 화면 보기(status)와 게임 바꾸기(switch)는 세지 않는다.
- 작업 시간은 최대 2시간 (첫 명령부터). 모든 행동은 시각과 함께 log.jsonl 에 기록된다.

## 조작 (이 폴더에서 실행)
- `python3 /home/user/1-ai-/tools/arc_play.py status` : 지금 화면을 `frame.png` 로 저장하고 상태(JSON) 출력
- `python3 /home/user/1-ai-/tools/arc_play.py switch <1|2|3>` : 게임 바꾸기
- `python3 /home/user/1-ai-/tools/arc_play.py act <행동> [<행동> ...]` : 한 번에 최대 10개
  - 행동: `up` `down` `left` `right` `space` `undo` `reset` `click:X,Y` (X,Y 는 0~63 칸 좌표, 그림 가장자리 눈금 참고)
- 화면 보기: Read 도구로 `frame.png` 를 연다 (64×64 칸, 8칸마다 눈금과 좌표).

## 금지
- 게임 소스 코드·엔진·도구 내부를 읽지 않는다 (/home/user/1-ai-/ 아래 아무것도 열지 않는다). 인터넷 없음. log.jsonl 을 고치지 않는다.
