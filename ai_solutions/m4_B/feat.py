import numpy as np, cv2, tempfile, os

def decode_mp4_bytes(b):
    fd, p = tempfile.mkstemp(suffix=".mp4")
    try:
        with os.fdopen(fd, "wb") as f: f.write(b)
        return decode_mp4(p)
    finally:
        os.unlink(p)

def decode_mp4(p):
    cap = cv2.VideoCapture(p)
    fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        if f.ndim == 3: f = f[:, :, 0]
        fr.append(f)
    cap.release()
    return np.stack(fr).astype(np.float32)

def motion_feature(frames, step=1, out=128):
    """Motion-compensated residuals: background moves +2px/frame, fg -2px/frame (x axis).
    rb: residual under bg-motion hypothesis, rf: under fg-motion hypothesis."""
    F = frames
    a = F[step:]; b = F[:-step]
    d = 2 * step
    rb = np.abs(a - np.roll(b, d, axis=2)).mean(0)
    rf = np.abs(a - np.roll(b, -d, axis=2)).mean(0)
    s = (rb - rf) / (rb + rf + 1e-3)   # +1 text-like, -1 background-like
    x = np.stack([s, rb / 255.0, rf / 255.0])
    x = np.stack([cv2.resize(c, (out, out), interpolation=cv2.INTER_AREA) for c in x])
    return x.astype(np.float32)
