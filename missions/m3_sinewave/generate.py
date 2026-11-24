"""미션 3: 소리 착시 캡차 문제 만들기 (IllusionAudio 방식, 사인파 음성).

IllusionAudio (arXiv:2601.08516)에서 따른 것
  - 사인파 음성(sine-wave speech): 말소리를 사인파 몇 개로만 다시 만든 소리. 처음 들으면 삐-뿌- 하는 소리인데,
    원래 말을 한 번 들으면 갑자기 말로 들린다. 논문은 이 착시로 사람과 AI의 차이를 만든다.
  - 깨끗한 원본 음성을 먼저 들려준다 (논문: 원본이 없으면 사람도 못 알아듣는다, 원본이 '귀를 여는' 역할).
  - 사인파로 바꾼 뒤 '되돌릴 수 없는 무작위 다운샘플링'을 한 번 더 한다. 논문은 정확한 값을 공개하지 않아서
    여기서는 분석 프레임을 무작위 길이(1~3프레임)로 붙잡아 두는 방식으로 시간 정보를 일부 버린다.
사인파 음성 변환: johnhw/sinewave_speech (MIT, third_party/sinewave_speech/sws.py, 수정 없이 함수만 불러 씀)

문제 방식(사용자 사양): 원본 음성을 듣고 → 사인파 음성 4개 중 같은 문장을 고른다. 5문제, 하나라도 틀리면 실패.
오답 선택지는 정답 문장과 낱말이 겹치는 문장을 먼저 고른다 (예: 누나가 노래를 불러요 / 오리가 노래를 불러요).
기본 문장 20개는 모두 9글자(3어절 × 3글자)라 길이로는 구별이 안 된다.
영상용 홍보 멘트 4개(구독/좋아요/댓글/알림 … 제 기분이 좋아져요)는 서로 오답 선택지가 되고, '구독' 문장은 첫 판 5번 문제로 고정.

원본 음성: audio/originals/s01.wav ~ (sentences.txt 순서). 사용자의 컴퓨터 내장 한국어 TTS로 만든다:
  맥: bash tools/make_tts_mac.sh   윈도우: powershell -ExecutionPolicy Bypass -File tools\\make_tts_windows.ps1
정답은 평문으로 저장하지 않고 HMAC 해시로만 저장한다.

실행: python -m missions.m3_sinewave.generate
"""
import json
import random
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal

from common.answer_hash import answer_hash, load_key

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "m3"
ORIG = ROOT / "audio" / "originals"
SENTENCES = [l.strip() for l in (Path(__file__).parent / "sentences.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

sys.path.insert(0, str(ROOT / "third_party" / "sinewave_speech"))
if not hasattr(scipy.signal, "hann"):  # 최신 scipy 에서 옮겨진 함수 (sws.py 는 그대로 두고 이름만 연결)
    scipy.signal.hann = scipy.signal.windows.hann
import sws  # noqa: E402

SR = 22050  # 웹에서 재생할 소리의 표본 주파수


def load_cfg_and_seed() -> tuple[dict, int]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["m3"]
    seed = json.loads((ROOT / "secrets" / "seeds.json").read_text(encoding="utf-8"))["m3"]
    return cfg, seed


def load_original(i: int) -> np.ndarray:
    """s01.wav ... 를 22050Hz 모노 float 로."""
    sr, w = wavfile.read(ORIG / f"s{i + 1:02d}.wav")
    w = w.astype(np.float64)
    if w.ndim > 1:
        w = w.mean(axis=1)
    w /= (np.abs(w).max() + 1e-9)
    if sr != SR:
        g = np.gcd(int(sr), SR)
        w = scipy.signal.resample_poly(w, SR // g, int(sr) // g)
    # 앞뒤 무음 자르기
    a = np.abs(w)
    idx = np.where(a > 0.02)[0]
    if len(idx):
        w = w[max(0, idx[0] - 600): idx[-1] + 1200]
    return w


def sinewave(wave: np.ndarray, cfg: dict, rng: random.Random) -> np.ndarray:
    """sws.py 의 분석·합성 함수로 사인파 음성을 만들되, 합성 전에 프레임을 무작위로 붙잡아 둔다(되돌릴 수 없는 다운샘플링)."""
    dec = cfg["decimate"]
    fs = SR / dec
    x = sws.normalize(sws.bp_filter_and_decimate(wave, cfg["low"], cfg["high"], SR, decimate=dec))
    frame_len, order = cfg["window"], 2 * cfg["order"] + 2
    hop = int(frame_len * cfg["overlap"])
    times, lsps, env = sws.get_lsp(x, frame_len, order, fs, hop)
    formants, bws = sws.formants_from_lsp(lsps, fs)
    # 무작위 붙잡기: 1~max_hold 프레임 동안 같은 값을 유지
    k = 0
    while k < len(formants):
        h = rng.randint(1, cfg["max_hold"])
        formants[k:k + h] = formants[k]
        bws[k:k + h] = bws[k]
        k += h
    out = np.zeros_like(x)
    window = scipy.signal.windows.hann(frame_len)
    t = np.arange(0.0, frame_len)
    k = 0
    for i in range(0, len(x), hop):  # sws.sinethesise 와 같은 합성 (값만 위에서 바꾼 것 사용)
        if len(out[i:i + frame_len]) == frame_len and k < len(formants):
            s = np.zeros_like(t)
            for band in range(formants.shape[1]):
                f, bw = formants[k, band], bws[k, band]
                if f > 90.0:
                    s += np.sin(f * (t + i) / (fs / (2 * np.pi))) * np.exp(bw / cfg["bw_amp"])
            out[i:i + frame_len] += window * s * env[k]
        k += 1
    return sws.normalize(sws.upsample(out, dec))


def write_wav(path: Path, w: np.ndarray, peak: float = 0.8) -> None:
    w = w / (np.abs(w).max() + 1e-9) * peak
    wavfile.write(path, SR, (w * 32767).astype(np.int16))


def _group(i: int) -> str:
    """기본 문장(9글자)과 홍보 멘트(… 제 기분이 좋아져요)는 서로 섞지 않는다 (길이로 티 나지 않게)."""
    return "promo" if SENTENCES[i].endswith("제 기분이 좋아져요") else "basic"


def pick_distractors(target: int, rng: random.Random, n: int = 3) -> list[int]:
    """정답 문장과 낱말이 겹치는 문장을 먼저, 모자라면 아무 문장."""
    words = set(SENTENCES[target].split())
    group = [i for i in range(len(SENTENCES)) if i != target and _group(i) == _group(target)]  # 길이가 같은 무리끼리만
    share = [i for i in group if words & set(SENTENCES[i].split())]
    rng.shuffle(share)
    rest = [i for i in group if i not in share]
    rng.shuffle(rest)
    return (share + rest)[:n]


def iter_problems(seed: int, cfg: dict):
    rng = random.Random(seed)
    order = list(range(len(SENTENCES)))
    rng.shuffle(order)
    # 영상용: '구독' 문장은 첫 판 마지막 문제(5번)로 고정
    sub = SENTENCES.index(cfg["fixed_q5_sentence"]) if cfg.get("fixed_q5_sentence") in SENTENCES else None
    if sub is not None:
        order.remove(sub)
        order.insert(cfg["questions_per_round"] - 1, sub)
    for q in range(1, cfg["pool_size"] + 1):
        target = order[(q - 1) % len(order)]
        opts = [target] + pick_distractors(target, rng)
        rng.shuffle(opts)
        yield q, target, opts, rng.getrandbits(32)


def main() -> None:
    cfg, seed = load_cfg_and_seed()
    missing = [i for i in range(len(SENTENCES)) if not (ORIG / f"s{i + 1:02d}.wav").exists()]
    if missing:
        raise SystemExit(f"원본 음성이 없습니다: {[f's{i + 1:02d}.wav' for i in missing]}. tools/make_tts_mac.sh 로 먼저 만드세요.")
    voice = (ORIG / "VOICE.txt").read_text().strip() if (ORIG / "VOICE.txt").exists() else "unknown"
    key = load_key(create=True)
    originals = [load_original(i) for i in range(len(SENTENCES))]
    if OUT.exists():
        shutil.rmtree(OUT)
    questions = []
    for q, target, opts, clip_seed in iter_problems(seed, cfg):
        rng = random.Random(clip_seed)
        d = OUT / "audio" / f"q{q:02d}"
        d.mkdir(parents=True)
        write_wav(d / "ref.wav", originals[target])
        for n, s in enumerate(opts, 1):
            write_wav(d / f"opt{n}.wav", sinewave(originals[s], cfg, rng))
        correct = opts.index(target) + 1
        questions.append({"q": q, "dir": f"q{q:02d}", "hash": answer_hash(key, "m3", q, str(correct))})
        print(f"  q{q:02d} 완료", flush=True)
    manifest = {"mission": "m3", "voice": voice,
                "answer_rule": "원본(ref.wav)과 같은 문장의 사인파 음성 번호(1~4)를 고른다",
                "questions": questions}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data/m3: 문제 {len(questions)}개 생성 (원본 음성: {voice}, 정답은 해시로만 저장)")


if __name__ == "__main__":
    main()
