"""In-memory version of the official generate_single() frame composition (no mp4 codec)."""
import numpy as np, time
from MVCAP_code.L1.config import BG_SPEED, FG_SPEED
def synth_frames(g, text):
    text_mask = g.build_text_mask(text)
    tex_bg = g.generate_dot_texture(g.height, g.width)
    tex_fg = g.generate_dot_texture(g.height, g.width)
    fr = np.empty((g.total_frames, g.height, g.width), np.float32)
    for i in range(g.total_frames):
        f = np.roll(tex_bg, i * BG_SPEED, axis=1)
        f[text_mask] = np.roll(tex_fg, i * FG_SPEED, axis=1)[text_mask]
        fr[i] = f
    return fr
