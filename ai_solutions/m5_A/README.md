# 과제: ARC-AGI-3 게임 3개 직접 플레이 (미션 5)

처음 보는 퍼즐 게임 3개(1: ls20, 2: ft09, 3: vc33)를 **화면을 보고 행동을 하나씩 골라** 플레이한다. 규칙 설명은 없다 (사람도 같음).
각 게임은 여러 단계(level)로 되어 있고, 단계를 깨면 다음 단계로 넘어간다. 목표: 30분 안에 최대한 많은 단계를 깨기 (모든 게임 완료 = 성공).

## 조작 (이 폴더에서 실행)
- `python3 /home/user/1-ai-/tools/arc_play.py status` : 지금 화면을 `frame.png` 로 저장하고 상태(JSON) 출력
- `python3 /home/user/1-ai-/tools/arc_play.py switch <1|2|3>` : 게임 바꾸기
- `python3 /home/user/1-ai-/tools/arc_play.py act <행동> [<행동> ...]` : 한 번에 최대 5개
  - 행동: `up` `down` `left` `right` `space` `undo` `reset` `click:X,Y` (X,Y 는 0~63 칸 좌표, 그림 가장자리의 숫자 눈금 참고)
  - 게임마다 쓸 수 있는 행동은 status 의 available_actions 에 나온다.
- 화면 보기: Read 도구로 `frame.png` 를 연다 (64×64 칸, 8칸마다 눈금과 좌표).

## 제한
- 시간 30분 (첫 명령부터), 행동 300번. 넘으면 도구가 더 받지 않는다. 모든 행동은 시각과 함께 log.jsonl 에 기록된다.
- 게임 소스 코드나 엔진, 도구 내부를 읽지 않는다 (/home/user/1-ai-/ 아래 아무것도 열지 않는다). 인터넷 없음.
- 기록(log.jsonl)을 직접 고치지 않는다.
