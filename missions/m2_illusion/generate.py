"""미션 2: 착시 캡차 문제 만들기 (IllusionCAPTCHA 방식 + 하이브리드 이미지).

하이브리드 이미지 (Oliva·Torralba·Schyns, SIGGRAPH 2006):
  저주파 = 글자 이미지를 크게 블러한 것   → 눈을 가늘게 뜨거나 멀리서 보면 글자
  고주파 = 배경 그림 - 배경 그림의 블러    → 가까이서 보면 그림(숲·나뭇잎·풀밭)
  둘을 더해 한 장으로 만든다. 배경 그림은 저작권 걱정이 없도록 OpenCV로 직접 그린다.

IllusionCAPTCHA (Ding 외, arXiv:2502.05461)에서 따른 것
  - 숨은 내용은 짧고 익숙한 낱말 (논문: "day", "sun" 같은 영어 낱말 → 여기서는 두 글자 한국어 낱말)
  - 선택지 4개, 그중 하나는 그림을 만들 때 쓴 장면 문구 (논문: "huge forest" 같은 프롬프트) = 가까이 보면 보이는 함정
  - 후보 그림을 여러 장 만들어 숨은 내용이 가장 덜 드러나는 것을 고른다
    (논문: 50장 중 원본과 코사인 유사도가 가장 낮은 것 → 여기서는 후보 N장 중 글자 모양과 상관이 가장 낮은 것)
논문과 다른 점 (사용자 요청)
  - 논문의 나머지 두 선택지는 '장면을 길게 설명한 문장'이라 낱말 선택지가 하나뿐이어서 사람에게는 너무 쉽다.
    그래서 나머지 두 개는 정답과 첫 글자가 같은 두 글자 낱말(사과/사고/사자, 도끼/토끼 …)로 바꿨다.
    흐릿하게 보이는 글자를 정말 읽어야만 고를 수 있다.
  - 논문은 확산 모델(ControlNet)로 착시 그림을 만들지만, 외부 모델 없이 하이브리드 이미지로 만든다.

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

# 숨은 낱말: 첫 글자가 같은 두 글자 낱말 4개씩 한 묶음. 정답이 한 묶음에서 나오면 나머지 중 2개가 오답 선택지.
WORD_SETS = [g.split() for g in """
사과 사고 사자 사기 | 도끼 토끼 도기 토기 | 모자 모기 모래 모이 | 고래 고리 고기 고무
나비 나무 나라 나이 | 기차 기자 기사 기와 | 우유 우주 우산 우비 | 시계 시간 시장 시소
연필 연기 연못 연극 | 구름 구두 구멍 구슬 | 거울 거리 거미 거북 | 포도 포크 포장 포기
수박 수건 수레 수염 | 감자 감기 감옥 감독 | 하마 하늘 하루 하품 | 버스 버섯 버터 버튼
열쇠 열차 열매 열기 | 장갑 장미 장난 장화 | 피자 피리 피부 피망 | 커피 커튼 커플 커서
마을 마음 마술 마차 | 공원 공기 공부 공장 | 지도 지구 지붕 지갑 | 보물 보리 보석 보트
소리 소금 소풍 소원 | 오리 오이 오늘 오후 | 사탕 사슴 사진 사막 | 바다 바지 바람 바위
가방 가게 가위 가지 | 도시 도로 도장 도마 | 노래 노을 노트 노인 | 주사 주소 주인 주말
비누 비옷 비밀 비용 | 달력 달걀 달빛 달인
""".replace("\n", "|").split("|") if g.strip()]
WORDS = [w for g in WORD_SETS for w in g]
assert all(len(g) == 4 for g in WORD_SETS) and len(set(WORDS)) == len(WORDS)

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
    mask = text_mask(word, w, h, cfg)
    # 글자 위치·기울기를 조금씩 흔든다
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-6, 6), rng.uniform(.92, 1.04))
    m[:, 2] += (rng.uniform(-.06, .06) * w, rng.uniform(-.06, .06) * h)
    mask = cv2.warpAffine(mask, m, (w, h))
    t = cv2.GaussianBlur(mask, (0, 0), cfg["sigma_low"])                # 글자의 저주파
    t = t - t.mean()
    # 위장: 글자와 비슷한 크기의 흐릿한 얼룩을 섞어 글자만 도드라지지 않게
    noise = np.asarray([[rng.gauss(0, 1) for _ in range(w // 16)] for _ in range(h // 16)], np.float32)
    camo = cv2.GaussianBlur(cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), cfg["sigma_low"])
    camo = camo / (camo.std() + 1e-6) * t.std()
    out = base + cfg["high_gain"] * hi - cfg["text_amp"] * (t + cfg["camo"] * camo)[..., None]
    img = (np.clip(out, 0, 1) * 255).astype(np.uint8)
    return img, mask


def text_visibility(img: np.ndarray, mask: np.ndarray) -> float:
    """멀리서 본 그림(크게 줄인 것)과 글자 모양의 상관. 낮을수록 글자가 덜 드러난다."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    small = cv2.resize(g, (48, 30), interpolation=cv2.INTER_AREA).ravel()
    ms = cv2.resize(mask, (48, 30), interpolation=cv2.INTER_AREA).ravel()
    return float(-np.corrcoef(small, ms)[0, 1])  # 글자가 어두우니 부호를 뒤집음


def make_image(word: str, scene: str, rng: random.Random, cfg: dict) -> tuple[np.ndarray, float]:
    """후보를 여러 장 만들어, 글자가 '보이긴 하지만 가장 덜 드러나는' 것을 고른다 (논문의 후보 선택 방식)."""
    best = None
    for _ in range(cfg["candidates"]):
        img, mask = hybrid(word, scene, rng, cfg)
        v = text_visibility(img, mask)
        if v < cfg["min_visibility"]:
            continue  # 너무 안 보이는 후보는 버림 (사람도 못 푸는 문제 방지)
        if best is None or v < best[1]:
            best = (img, v)
    if best is None:  # 모두 너무 안 보이면 가장 잘 보이는 후보
        img, mask = hybrid(word, scene, rng, cfg)
        best = (img, text_visibility(img, mask))
    return best


def iter_problems(seed: int, cfg: dict):
    """(문제 번호, 정답 낱말, 장면, 선택지 4개, 그림 시드) 를 차례로."""
    rng = random.Random(seed)
    scenes = list(SCENES)
    prev = []
    for q in range(1, cfg["pool_size"] + 1):
        group = rng.choice([g for g in WORD_SETS if not set(g) & set(prev)])  # 가까운 문제끼리 같은 묶음 안 나오게
        word = rng.choice(group)
        prev = (prev + group)[-40:]
        scene = rng.choice(scenes)
        wrong = rng.sample([x for x in group if x != word], 2)
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
        img, vis = make_image(word, scene, random.Random(img_seed), cfg)
        name = f"q{q:03d}.jpg"
        cv2.imwrite(str(img_dir / name), img, [cv2.IMWRITE_JPEG_QUALITY, cfg["jpeg_quality"]])
        questions.append({"q": q, "file": name, "choices": choices, "hash": answer_hash(key, "m2", q, word)})
        if q % 20 == 0:
            print(f"  {q}문제 완료", flush=True)
    manifest = {
        "mission": "m2",
        "answer_rule": "4개 선택지 중 그림에 숨은 글자를 고른다 (선택지 글자 그대로 비교)",
        "questions": questions,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data/m2: 문제 {len(questions)}개 생성 (정답은 해시로만 저장)")


if __name__ == "__main__":
    main()
