"""미션 3 AI 학습용 '정답 달린 소리 캡차' 묶음 (현실의 라벨링 공격 흉내, 미션 2와 같은 방식).

IllusionAudio 는 공식 코드가 공개되지 않아, 공격자는 실제 캡차를 모아 사람에게 정답(1~4)을 달게 해서 학습한다.
여기서는 시험 문제와 **다른 시드**로 같은 방식의 문제를 만들어 정답 번호만 붙여 준다.
- 문장 목록·목소리는 실제 서비스처럼 같다 (공격자가 모으는 캡차도 같은 문장에서 나오므로).
- 소리 파일은 시험과 다르다: 사인파 변환의 무작위 붙잡기, 앞 무음, 오답 조합, 보기 순서가 모두 다른 무작위.
- 문장 글자(텍스트)는 주지 않는다. 생성 코드·시드·시험 문제도 주지 않는다.

실행: python -m tools.make_m3_trainset <출력 폴더> <개수> [--seed 9001] [--workers 4]
"""
import argparse
import json
from multiprocessing import Pool
from pathlib import Path

from missions.m3_sinewave import generate as g

CFG = ORIG = None


def _init(cfg):
    global CFG, ORIG
    CFG = cfg
    ORIG = [g.load_original(i) for i in range(len(g.SENTENCES))]


def _make(job):
    i, target, opts, seed, out = job
    d = Path(out) / f"t{i:05d}"
    ans = g.write_question(d, target, opts, seed, ORIG, CFG)
    return {"dir": d.name, "answer": ans}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("count", type=int)
    ap.add_argument("--seed", type=int, default=9001)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cfg, test_seed = g.load_cfg_and_seed()
    assert a.seed != test_seed, "시험 문제와 같은 시드는 쓸 수 없음"
    cfg = dict(cfg, pool_size=a.count, fixed_q5_sentence=None)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(q, t, o, sd, str(out)) for q, t, o, sd in g.iter_problems(a.seed, cfg)]
    with Pool(a.workers, initializer=_init, initargs=(cfg,)) as pool:
        rows = list(pool.imap(_make, jobs, chunksize=16))
    (out / "labels.json").write_text(json.dumps(rows, indent=0), encoding="utf-8")
    print(f"{out}: 정답 달린 소리 캡차 {len(rows)}개")


if __name__ == "__main__":
    main()
