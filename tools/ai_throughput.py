"""미션 1·2 (B) 코드로 풀기: "1분 동안 최대 몇 문제" 측정.

AI가 만든 solver.py 로 ai_test/m1/images 의 문제를 1번부터 순서대로 풀고,
답과 시각을 ai_test/_log 에 남긴다 (사람 규칙과 같은 순서, 같은 문제).
채점은 그 뒤에 python -m tools.grade_ai m1 B 로 한다.

실행: python -m tools.ai_throughput <solver.py 폴더> [--seconds 60] [--mission m2 --mode B-orig]
      (미션 2 줄인 그림: --mission m2 --mode B-small --image small)
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai_test"))
from submit import record  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("solver_dir")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--mission", default="m1")
    ap.add_argument("--mode", default="B")
    ap.add_argument("--image", default="file", help="questions.json 의 그림 열 (미션 2: file 또는 small)")
    args = ap.parse_args()

    folder = Path(args.solver_dir).resolve()
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("solver", folder / "solver.py")
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)  # 모델 로드 (시간 측정 전)

    m, mode = args.mission, args.mode
    questions = json.loads((ROOT / "ai_test" / m / "questions.json").read_text(encoding="utf-8"))
    images = [(q["q"], (ROOT / "ai_test" / m / q[args.image]).read_bytes(), q.get("choices")) for q in questions]
    run = (lambda png, ch: solver.solve(png, ch)) if m == "m2" else (lambda png, ch: solver.solve(png))
    run(images[-1][1], images[-1][2])  # 예열

    record(m, mode, "start")
    record(m, mode, "mark", label="ready")  # 프로그램은 이미 준비된 상태에서 시작
    t0 = time.perf_counter()
    n = 0
    for q, png, ch in images:
        if time.perf_counter() - t0 > args.seconds:
            break
        record(m, mode, "answer", q=q, answer=run(png, ch))
        n += 1
    record(m, mode, "end")
    print(f"{args.seconds:.0f}초 동안 {n}문제 제출 (문제가 {len(images)}개라 다 풀면 거기서 멈춤)")


if __name__ == "__main__":
    main()
