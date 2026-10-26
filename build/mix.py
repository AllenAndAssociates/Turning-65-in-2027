"""Mix voice (with flub cut), music bed and frame-synced SFX -> build/out/mix.wav"""
import os
import subprocess
import numpy as np
from timeline import *

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Untitled video.mp4")
OUT = os.path.join(HERE, "out")
SR = 48000
os.makedirs(OUT, exist_ok=True)


def load(path, af=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def db(x):
    return 10 ** (x / 20)


n = int(END * SR)
mix = np.zeros((n, 2), np.float32)

# Voice: cut the flub, loudness-normalise to -15 LUFS
voice = load(SRC, f"aselect='not(between(t,{CUT_IN},{CUT_OUT}))',asetpts=N/SR/TB,"
                  "loudnorm=I=-15:TP=-1.5:LRA=11")
voice = voice[:n]
mix[:len(voice)] += voice

# Music bed at -26 LUFS, brief pause on "two main paths", warm swell to -22 for the CTA
music = load(os.path.join(HERE, "audio", "music.mp3"), "loudnorm=I=-26:TP=-6:LRA=11")
m = np.zeros((n, 2), np.float32)
m[:min(n, len(music))] = music[:n]
t = np.arange(n) / SR
gain = np.ones(n)
p0, p1 = T_TWO_PATHS - 0.12, T_TWO_PATHS + 1.25
gain *= np.clip(np.maximum((p0 - t) / 0.05, (t - p1) / 0.25), 0, 1)       # pause
gain *= db(np.clip((t - S7) / 1.5, 0, 1) * 4.0)                             # swell +4 dB
gain *= np.clip((END - t) / 1.2, 0, 1)                                       # tail fade
mix += m * gain[:, None].astype(np.float32)

# SFX: (name, time, level dB relative to a -12 dBFS-peak normalised clip)
SFX = [
    ("drop", 0.00, -6),
    ("tick", 1.00, -4), ("tick", 1.15, -4), ("tick", 1.30, -4),
    ("uipop", 0.55, -8),
    ("uipop", T_DO_NOT, -10),
    ("static", T_STATIC_OFF - 0.25, -10),
    ("drop", S2, -6),
    ("cardpop", S3, -4),
    ("uipop", T_OCT15, -6), ("uipop", T_DEC7, -6),
    ("highlight", T_ONLY, -6),
    ("stamp", T_STAMP, -3),
    ("chime", T_GREEN, -6),
    ("snap", S5, -4),
    ("whoosh", T_SIX_NINE - 0.25, -6), ("ping", T_SIX_NINE + 0.2, -8),
    ("click", T_TWO_PATHS - 0.12, -4),
    ("uipop", T_PATH_A, -5), ("uipop", T_PATH_B, -5),
    ("drop", S7, -6),
    ("mouse", T_URL, -4),
    ("chord", T_CHORD, -8),
] + [("dial", td, -22 + 12) for td in T_DIGITS]  # dial ticks mixed low (≈ -22 dB) under the voice

cache = {}
for name, ts, lvl in SFX:
    if name not in cache:
        c = load(os.path.join(HERE, "audio", "sfx", name + ".mp3"))
        c = c / (np.abs(c).max() + 1e-9) * db(-12)
        cache[name] = c
    c = cache[name] * db(lvl)
    if name == "dial":
        c = c[: int(0.16 * SR)] * np.linspace(1, 0, int(0.16 * SR))[:, None]
    i = int(ts * SR)
    j = min(n, i + len(c))
    mix[i:j] += c[: j - i]

raw = os.path.join(OUT, "mix_raw.f32")
mix.astype(np.float32).tofile(raw)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw,
                "-af", "alimiter=limit=0.89:attack=3:release=50", "-c:a", "pcm_s16le",
                os.path.join(OUT, "mix.wav")], check=True)
os.remove(raw)
print("mix ok", END)
