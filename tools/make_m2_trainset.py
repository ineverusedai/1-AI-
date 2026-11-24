"""미션 2 AI 학습용 '정답 달린 캡차' 묶음 만들기 (현실의 공격 방식 흉내).

실제 공격자는 목표 캡차를 대량으로 모은 뒤 사람에게 정답을 달게 해서(라벨링) 전용 모델을 학습한다.
여기서는 시험 문제와 **다른 시드**로 같은 방식의 캡차를 만들어 정답을 붙여 준다.
시험 문제(ai_test/m2, 시드는 secrets/)와 그림·순서가 겹치지 않는다. 생성 코드는 AI에게 주지 않는다.

실행: python -m tools.make_m2_trainset <출력 폴더> <개수> [--seed 7001] [--workers 4]
"""
import argparse
import json
import random
from multiprocessing import Pool
from pathlib import Path

import cv2

from missions.m2_illusion import generate as g

CFG = None


def _init(cfg):
    global CFG
    CFG = cfg


def _make(job):
    i, word, scene, choices, img_seed, out = job
    img, _ = g.make_image(word, scene, random.Random(img_seed), CFG)
    name = f"t{i:05d}.jpg"
    cv2.imwrite(str(Path(out) / "images" / name), img, [cv2.IMWRITE_JPEG_QUALITY, CFG["jpeg_quality"]])
    return {"file": "images/" + name, "choices": choices, "answer": word}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("count", type=int)
    ap.add_argument("--seed", type=int, default=7001)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    cfg, test_seed = g.load_cfg_and_seed()
    assert args.seed != test_seed, "시험 문제와 같은 시드는 쓸 수 없음"
    cfg = dict(cfg, pool_size=args.count)
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    jobs = [(q, w, s, c, sd, str(out)) for q, w, s, c, sd in g.iter_problems(args.seed, cfg)]
    rows = []
    with Pool(args.workers, initializer=_init, initargs=(cfg,)) as pool:
        for k, r in enumerate(pool.imap(_make, jobs, chunksize=8), 1):
            rows.append(r)
            if k % 250 == 0:
                print(f"  {k}/{len(jobs)}", flush=True)
    (out / "labels.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{out}: 정답 달린 캡차 {len(rows)}장")


if __name__ == "__main__":
    main()
