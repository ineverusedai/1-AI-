"""AI가 만든 solver.py 를 불러서 한 줄씩 문제를 풀어 주는 다리.

AI의 코드(solver.py)는 `solve(png_bytes: bytes) -> str` 하나만 있으면 된다.
이 파일은 정답·시드·키를 전혀 모른다. 이미지를 넘기고 답을 돌려받을 뿐이다.

입력(표준 입력, 한 줄에 하나): {"png_b64": "..."}
출력(표준 출력, 한 줄에 하나):  {"answer": "...", "ms": 걸린 밀리초}
실행: python -I tools/solver_bridge.py <solver.py가 있는 폴더>
"""
import base64
import importlib.util
import json
import sys
import time
from pathlib import Path


def main() -> None:
    folder = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("solver", folder / "solver.py")
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        png = base64.b64decode(json.loads(line)["png_b64"])
        t = time.perf_counter()
        answer = str(solver.solve(png))
        print(json.dumps({"answer": answer, "ms": round((time.perf_counter() - t) * 1000, 2)}), flush=True)


if __name__ == "__main__":
    main()
