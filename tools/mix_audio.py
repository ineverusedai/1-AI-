"""녹화 도구용: 재생 기록(어떤 소리를 몇 초에 틀고 몇 초에 멈췄는지)대로 소리 파일을 깔아 wav 한 개로 만든다.

실행: python -m tools.mix_audio <plays.json> <출력 wav>
plays.json = {"plays": [{"src": 파일, "start": 초, "end": 초 또는 null}], "total": 전체 초}
"""
import json
import sys

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal

SR = 44100


def main() -> None:
    plan = json.loads(open(sys.argv[1], encoding="utf-8").read())
    out = np.zeros(int(plan["total"] * SR) + SR)
    for p in plan["plays"]:
        sr, w = wavfile.read(p["src"])
        w = w.astype(np.float64) / 32768.0
        if w.ndim > 1:
            w = w.mean(axis=1)
        if sr != SR:
            g = np.gcd(sr, SR)
            w = scipy.signal.resample_poly(w, SR // g, sr // g)
        a = int(p["start"] * SR)
        if p.get("end") is not None:
            w = w[: max(0, int((p["end"] - p["start"]) * SR))]
        w = w[: max(0, len(out) - a)]
        out[a:a + len(w)] += w
    out = np.clip(out, -1, 1)
    wavfile.write(sys.argv[2], SR, np.stack([out, out], axis=1).astype(np.float32))
    print(f"소리 {len(plan['plays'])}개를 깔아 {plan['total']:.1f}초 소리 트랙 생성")


if __name__ == "__main__":
    main()
