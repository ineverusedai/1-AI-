"""미션 4: 움직여야 보이는 캡차 문제 만들기 (MVCAP L1, 공식 코드 그대로).

MVCAP (Motion Vision CAPTCHA, ACM Multimedia 2026, zeyu1998/MVCAP, MIT)의 L1 생성기를 수정 없이 불러 쓴다.
  - 488×488, 30fps, 3초(90프레임) 영상. 점이 흩뿌려진 화면에서 배경 점은 오른쪽(+2px/프레임),
    글자 모양 안의 점은 왼쪽(−2px/프레임)으로 움직인다. 멈춘 한 장면에서는 흩어진 점뿐이고, 움직여야 4글자가 보인다.
  - 글자: 헷갈리는 글자를 뺀 32자 (ABCDEFGHJKLMNPQRSTUVWXYZ23456789), 4글자.
  - 선택지: 정답 + 무작위 오답 5개 = 6지선다, 섞어서 A~F (공식 VQA 파일과 같은 방식).
  - 영상 인코딩도 공식 코드 그대로 (H.264, 모든 프레임 키프레임, crf 20).
L2·L3는 ShapeNet·BABEL 등 서드파티 약관 때문에 쓰지 않는다 (사용자 사양).
정답 글자는 평문으로 저장하지 않고 HMAC 해시로만 저장. 정답 그림(answer PNG)은 만들자마자 지운다.

실행: python -m missions.m4_motion.generate
"""
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

from common.answer_hash import answer_hash, load_key

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "m4"
sys.path.insert(0, str(ROOT / "third_party" / "mvcap"))
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import (  # noqa: E402
    L1TextCaptchaGenerator, sample_distractors, sample_text)

LABELS = "ABCDEF"


def load_cfg_and_seed() -> tuple[dict, int]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m4"]
    seed = json.loads((ROOT / "secrets" / "seeds.json").read_text(encoding="utf-8"))["m4"]
    return cfg, seed


def main() -> None:
    cfg, seed = load_cfg_and_seed()
    key = load_key(create=True)
    np.random.seed(seed)          # 공식 코드처럼 점 무늬는 numpy 전역 난수
    rng = random.Random(seed)     # 글자·오답은 random.Random (공식 코드와 같은 함수)
    gen = L1TextCaptchaGenerator()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "videos").mkdir(parents=True)
    questions = []
    with tempfile.TemporaryDirectory() as tmp:
        for q in range(1, cfg["pool_size"] + 1):
            text = sample_text(rng)
            options = [text] + sample_distractors(rng, text)
            rng.shuffle(options)
            name = f"q{q:02d}.mp4"
            gen.generate_single(text, OUT / "videos" / name, Path(tmp) / "answer.png")  # 정답 그림은 임시 폴더에만
            questions.append({"q": q, "file": name, "options": options, "hash": answer_hash(key, "m4", q, text)})
            print(f"  q{q:02d} 완료", flush=True)
    manifest = {"mission": "m4", "source": "MVCAP L1 rigid_drift (공식 코드)",
                "answer_rule": "영상 속 4글자와 같은 선택지(A~F)를 고른다 (선택지 글자 그대로 비교)",
                "questions": questions}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data/m4: 문제 {len(questions)}개 생성 (정답은 해시로만 저장)")


if __name__ == "__main__":
    main()
