"""미션 1: 글자 캡차 문제 생성.

lepture/captcha 0.7.1은 내부에서 `secrets`(암호학적 난수)를 써서 시드를 줄 수 없다.
그래서 생성하는 동안만 captcha.image 모듈의 `secrets`를 시드가 고정된 난수로 바꿔 끼운다.
같은 시드 + 같은 라이브러리/Pillow 버전이면 같은 이미지가 나온다.

출력
  data/m1/images/q001.png ...   문제 이미지 (파일 이름에 정답 정보 없음)
  data/m1/manifest.json          문제 번호, 파일, 정답 HMAC (평문 없음)

실행: python -m missions.m1_captcha.generate
"""
import json
import random
import shutil
import string
import sys
from pathlib import Path

import captcha
import captcha.image as captcha_image
from captcha.image import ImageCaptcha

from common.answer_hash import answer_hash, load_key

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "m1"
MISSION = "m1"

# 헷갈리는 글자: 숫자 0 / 대문자 O / 숫자 1 / 소문자 l(엘) / 대문자 I(아이)
CONFUSABLES = "0O1lI"
# 나머지 글자: 대문자 + 숫자. 소문자는 l 하나만 나온다 (대소문자 구분)
OTHERS = "".join(c for c in string.ascii_uppercase + string.digits if c not in CONFUSABLES)
CHARSET_DESC = "대문자 A-Z, 숫자 0-9, 소문자는 l(엘) 하나만. 대소문자 구분."


class SeededSecrets:
    """`secrets` 모듈에서 captcha가 쓰는 함수만 시드 고정 난수로 흉내 낸다."""

    def __init__(self, rng: random.Random):
        self._r = rng

    def randbelow(self, n: int) -> int:
        return self._r.randrange(n)

    def randbits(self, k: int) -> int:
        return self._r.getrandbits(k)

    def choice(self, seq):
        return self._r.choice(seq)


def make_text(rng: random.Random, length: int, min_conf: int) -> str:
    n_conf = rng.randint(min_conf, min(length, min_conf + 1))
    chars = [rng.choice(CONFUSABLES) for _ in range(n_conf)]
    chars += [rng.choice(OTHERS) for _ in range(length - n_conf)]
    rng.shuffle(chars)
    return "".join(chars)


def iter_problems(seed: int, cfg: dict):
    """(문제 번호, 정답, 이미지 난수 시드)를 순서대로 돌려준다. 정답은 메모리에만 존재."""
    text_rng = random.Random(f"m1-text-{seed}")
    for q in range(1, cfg["pool_size"] + 1):
        yield q, make_text(text_rng, cfg["length"], cfg["min_confusables"]), f"m1-img-{seed}-{q}"


def load_cfg_and_seed():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m1"]
    seed = json.loads((ROOT / "secrets" / "seeds.json").read_text(encoding="utf-8"))["m1"]
    return cfg, seed


def main() -> None:
    cfg, seed = load_cfg_and_seed()
    key = load_key(create=True)

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "images").mkdir(parents=True)

    gen = ImageCaptcha(width=cfg["width"], height=cfg["height"])
    original_secrets = captcha_image.secrets
    questions = []
    try:
        for q, text, img_seed in iter_problems(seed, cfg):
            captcha_image.secrets = SeededSecrets(random.Random(img_seed))
            fname = f"q{q:03d}.png"
            gen.write(text, str(OUT / "images" / fname))
            questions.append({"q": q, "file": fname, "hash": answer_hash(key, MISSION, q, text)})
    finally:
        captcha_image.secrets = original_secrets

    manifest = {
        "mission": MISSION,
        "title": cfg["title"],
        "count": len(questions),
        "answer_rule": CHARSET_DESC,
        "generator": f"captcha {getattr(captcha, '__version__', '0.7.1')} (lepture/captcha, BSD-3-Clause)",
        "questions": questions,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"미션 1: 문제 {len(questions)}개 생성 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
