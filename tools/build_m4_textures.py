"""미션 4 웹용 '재료' 파일 만들기: 영상 대신 공식 생성기의 점 무늬 2장 + 글자 모양을 한 장의 PNG 로.

공식 MVCAP L1 생성기(generate_single)는 매 프레임
  화면 = 배경 점 무늬를 오른쪽으로 2px×k 민 것, 단 글자 모양 안은 전경 점 무늬를 왼쪽으로 2px×k 민 것
을 만들어 mp4 로 저장한다. 브라우저가 같은 계산으로 직접 그리면 파일이 수십 KB 로 줄고 압축 손실도 없다.
data/m4/manifest.json 과 같은 시드·같은 순서로 다시 만들어, 기존 mp4 의 프레임과 픽셀 단위로 같은지 확인한다.

PNG 채널: R = 배경 점 무늬, G = 전경 점 무늬, B = 글자 모양 XOR 의사난수 (파일을 열어도 글자가 바로 보이지 않게).
의사난수: xorshift32, 시드 = (2463534242 ^ (문제번호 × 2654435761)) & 0xFFFFFFFF, 픽셀마다 최상위 비트. web_static/m4/ui.js 와 같다.

실행: python -m tools.build_m4_textures
"""
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "third_party" / "mvcap"))
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import (  # noqa: E402
    L1TextCaptchaGenerator, sample_distractors, sample_text)


def noise_bits(q: int, n: int) -> np.ndarray:
    x = (2463534242 ^ (q * 2654435761)) & 0xFFFFFFFF
    out = np.empty(n, np.uint8)
    for i in range(n):
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        out[i] = x >> 31
    return out


def main() -> None:
    seed = json.loads((ROOT / "secrets" / "seeds.json").read_text(encoding="utf-8"))["m4"]
    man = json.loads((ROOT / "data" / "m4" / "manifest.json").read_text(encoding="utf-8"))["questions"]
    np.random.seed(seed)
    rng = random.Random(seed)
    g = L1TextCaptchaGenerator()
    out = ROOT / "data" / "m4" / "tex"
    out.mkdir(parents=True, exist_ok=True)
    for q in man:
        text = sample_text(rng)
        opts = [text] + sample_distractors(rng, text)
        rng.shuffle(opts)
        assert opts == q["options"], "manifest 와 순서가 다름"
        mask = g.build_text_mask(text)
        bg = g.generate_dot_texture(g.height, g.width)
        fg = g.generate_dot_texture(g.height, g.width)
        # 기존 mp4 첫 3프레임과 비교 (압축 잡음 제외 같은지)
        cap = cv2.VideoCapture(str(ROOT / "data" / "m4" / "videos" / q["file"]))
        for k in range(3):
            ok, f = cap.read()
            exp = np.roll(bg, 2 * k, axis=1).copy()
            exp[mask] = np.roll(fg, -2 * k, axis=1)[mask]
            bad = np.mean(np.abs(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(int) - exp.astype(int)) > 128)
            assert bad < 1e-4, f"{q['file']} 프레임 {k} 이 다름 ({bad})"  # mp4 압축 때문에 픽셀 한두 개는 다를 수 있음
        enc = (mask.astype(np.uint8).ravel() ^ noise_bits(q["q"], mask.size)).reshape(mask.shape) * 255
        img = np.dstack([enc, fg, bg])  # OpenCV 는 BGR 순서 → 파일에는 R=bg, G=fg, B=enc
        cv2.imwrite(str(out / f"q{q['q']:02d}.png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(f"data/m4/tex: 재료 {len(man)}개 (기존 mp4 와 같음 확인: 압축 잡음 픽셀 0.01% 미만)")


if __name__ == "__main__":
    main()
