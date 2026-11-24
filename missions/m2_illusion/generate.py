"""미션 2: 착시 캡차 문제 만들기 (IllusionCAPTCHA 방식 + 하이브리드 이미지).

하이브리드 이미지 (Oliva·Torralba·Schyns, SIGGRAPH 2006):
  저주파 = 글자 이미지를 크게 블러한 것   → 눈을 가늘게 뜨거나 멀리서 보면 글자
  고주파 = 배경 그림 - 배경 그림의 블러    → 가까이서 보면 그림(숲·나뭇잎·풀밭)
  둘을 더해 한 장으로 만든다. 배경 그림은 저작권 걱정이 없도록 OpenCV로 직접 그린다.

문제마다 4지선다: 숨은 글자(정답), 장면 설명 1개(가까이 보면 보이는 것), 오답 단어 2개.
정답은 평문으로 저장하지 않고 HMAC 해시로만 저장한다 (manifest.json).

실행: python -m missions.m2_illusion.generate
"""
import json
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common.answer_hash import answer_hash, load_key

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "m2"
FONT = ROOT / "common" / "web" / "fonts" / "PretendardVariable.woff2"

# 숨은 글자로 쓰는 두세 글자 낱말 (장면과 상관없는 흔한 낱말)
WORDS = """사과 바다 하늘 기차 우유 나비 모자 의자 시계 연필 가방 우산 구름 호수 노래 편지
사진 거울 수박 포도 딸기 감자 양파 당근 토끼 사자 여우 고래 상어 오리 거북 하마
버스 택시 열쇠 안경 양말 장갑 치즈 라면 김밥 만두 피자 빵집 커피 녹차 주스 사탕
과자 별빛 달빛 눈사람 기린 낙타 판다 펭귄 고양이 강아지 다리 공원 학교 시장 은행
병원 극장 도시 마을 항구 섬나라 바람 번개 무지개 태양 지구 우주 로봇 풍선 인형 북극
남극 사막 화산 폭포 동굴 연못 등대 성벽 왕관 보물 지도 나침반 망원경 피아노 기타 드럼""".split()

# 가까이서 보면 보이는 장면 (선택지 중 '장면 설명')
SCENES = {
    "leaves": "나뭇잎이 쌓인 땅",
    "forest": "나무가 빽빽한 숲",
    "meadow": "꽃이 핀 풀밭",
}


def load_cfg_and_seed() -> tuple[dict, int]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m2"]
    seed = json.loads((ROOT / "secrets" / "seeds.json").read_text(encoding="utf-8"))["m2"]
    return cfg, seed


# ---------------- 배경 그림 (코드로 직접 그림) ----------------
def _col(rng, base, jit):
    return tuple(int(np.clip(c + rng.uniform(-jit, jit), 0, 255)) for c in base)


def draw_leaves(rng, w, h):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (30, 45, 60)  # BGR 어두운 흙색
    palette = [(40, 120, 60), (30, 150, 90), (20, 110, 160), (30, 80, 190), (40, 170, 210), (50, 140, 120)]
    for _ in range(int(w * h / 900)):
        cx, cy = rng.uniform(-20, w + 20), rng.uniform(-20, h + 20)
        L, W = rng.uniform(14, 42), rng.uniform(6, 16)
        ang = rng.uniform(0, 180)
        c = _col(rng, palette[rng.randrange(len(palette))], 30)
        cv2.ellipse(img, (int(cx), int(cy)), (int(L), int(W)), ang, 0, 360, c, -1, cv2.LINE_AA)
        dark = tuple(max(0, v - 55) for v in c)
        cv2.ellipse(img, (int(cx), int(cy)), (int(L), int(W)), ang, 0, 360, dark, 1, cv2.LINE_AA)
        dx, dy = np.cos(np.radians(ang)) * L, np.sin(np.radians(ang)) * L
        cv2.line(img, (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy)), dark, 1, cv2.LINE_AA)
    return img


def draw_forest(rng, w, h):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h):  # 위는 밝은 하늘빛, 아래는 어두운 숲 바닥
        t = y / h
        img[y] = (int(150 - 110 * t), int(170 - 110 * t), int(140 - 110 * t))
    for _ in range(int(w / 9)):  # 나무 줄기
        x = rng.uniform(0, w)
        tw = rng.uniform(5, 22)
        c = _col(rng, (40, 60, 85), 20)
        cv2.rectangle(img, (int(x), 0), (int(x + tw), h), c, -1)
        for _ in range(int(h / 14)):  # 나무껍질 무늬
            yy = rng.uniform(0, h)
            cv2.line(img, (int(x + 1), int(yy)), (int(x + tw - 1), int(yy + rng.uniform(-4, 4))), tuple(max(0, v - 30) for v in c), 1, cv2.LINE_AA)
    greens = [(40, 110, 40), (50, 140, 60), (30, 90, 50), (70, 160, 90), (40, 130, 110)]
    for _ in range(int(w * h / 260)):  # 잎 덩어리
        x, y = rng.uniform(0, w), rng.uniform(0, h) ** 1.0
        r = rng.uniform(3, 11)
        cv2.circle(img, (int(x), int(y)), int(r), _col(rng, greens[rng.randrange(len(greens))], 25), -1, cv2.LINE_AA)
    return img


def draw_meadow(rng, w, h):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (40, 110, 70)
    for _ in range(int(w * h / 60)):  # 풀잎
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        L = rng.uniform(8, 26)
        a = np.radians(rng.uniform(-115, -65))
        c = _col(rng, (50, 150, 90), 40)
        cv2.line(img, (int(x), int(y)), (int(x + np.cos(a) * L), int(y + np.sin(a) * L)), c, 1, cv2.LINE_AA)
    flowers = [(60, 60, 230), (230, 230, 240), (40, 200, 240), (200, 90, 200), (220, 140, 60)]
    for _ in range(int(w * h / 1500)):  # 꽃
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(3, 7)
        c = _col(rng, flowers[rng.randrange(len(flowers))], 25)
        for k in range(5):
            a = k * 2 * np.pi / 5 + rng.uniform(0, 1)
            cv2.circle(img, (int(x + np.cos(a) * r), int(y + np.sin(a) * r)), int(r * .7), c, -1, cv2.LINE_AA)
        cv2.circle(img, (int(x), int(y)), max(1, int(r * .45)), (40, 200, 250), -1, cv2.LINE_AA)
    return img


SCENE_DRAW = {"leaves": draw_leaves, "forest": draw_forest, "meadow": draw_meadow}


# ---------------- 글자 이미지 ----------------
def text_mask(word: str, w: int, h: int, cfg: dict) -> np.ndarray:
    """흰 바탕 0, 글자 1 인 float 마스크 (글자는 화면 가운데에 크게)."""
    size = int(h * cfg["text_height"])
    while True:
        font = ImageFont.truetype(str(FONT), size)
        try:
            font.set_variation_by_axes([cfg["font_weight"]])
        except Exception:
            pass
        img = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(img)
        l, t, r, b = d.textbbox((0, 0), word, font=font)
        if r - l <= w * cfg["text_max_width"] or size < 40:
            break
        size = int(size * 0.92)
    d.text(((w - (r - l)) / 2 - l, (h - (b - t)) / 2 - t), word, font=font, fill=255)
    return np.asarray(img, np.float32) / 255.0


# ---------------- 하이브리드 합성 ----------------
def hybrid(word: str, scene: str, rng: random.Random, cfg: dict) -> np.ndarray:
    w, h = cfg["width"], cfg["height"]
    bg = SCENE_DRAW[scene](rng, w, h).astype(np.float32) / 255.0
    hi = bg - cv2.GaussianBlur(bg, (0, 0), cfg["sigma_high"])            # 배경 그림의 고주파
    base = cv2.GaussianBlur(bg, (0, 0), cfg["sigma_base"])               # 아주 흐린 색감만
    t = cv2.GaussianBlur(text_mask(word, w, h, cfg), (0, 0), cfg["sigma_low"])  # 글자의 저주파
    t = t - t.mean()
    out = base + cfg["high_gain"] * hi - cfg["text_amp"] * t[..., None]
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def iter_problems(seed: int, cfg: dict):
    """(문제 번호, 정답 낱말, 장면, 선택지 4개, 그림 시드) 를 차례로."""
    rng = random.Random(seed)
    scenes = list(SCENES)
    prev = []
    for q in range(1, cfg["pool_size"] + 1):
        word = rng.choice([x for x in WORDS if x not in prev])
        prev = (prev + [word])[-20:]  # 가까운 문제끼리 같은 낱말 안 나오게
        scene = rng.choice(scenes)
        wrong = rng.sample([x for x in WORDS if x != word], 2)
        choices = [word, SCENES[scene]] + wrong
        rng.shuffle(choices)
        yield q, word, scene, choices, rng.getrandbits(32)


def main() -> None:
    cfg, seed = load_cfg_and_seed()
    key = load_key(create=True)
    img_dir = OUT / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for old in img_dir.glob("*"):
        old.unlink()
    questions = []
    for q, word, scene, choices, img_seed in iter_problems(seed, cfg):
        img = hybrid(word, scene, random.Random(img_seed), cfg)
        name = f"q{q:03d}.jpg"
        cv2.imwrite(str(img_dir / name), img, [cv2.IMWRITE_JPEG_QUALITY, cfg["jpeg_quality"]])
        questions.append({"q": q, "file": name, "choices": choices, "hash": answer_hash(key, "m2", q, word)})
    manifest = {
        "mission": "m2",
        "answer_rule": "4개 선택지 중 그림에 숨은 글자를 고른다 (선택지 글자 그대로 비교)",
        "questions": questions,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data/m2: 문제 {len(questions)}개 생성 (정답은 해시로만 저장)")


if __name__ == "__main__":
    main()
