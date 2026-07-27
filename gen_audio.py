"""DecideDeck's OWN royalty-free audio — synthesized from scratch (numpy).

Original on purpose: real music (even a "free" rip) risks a copyright claim,
which on a monetized channel costs that video's revenue. All SFX + the music bed
are generated here so the project ships self-contained.

Given a warmer, toy-piano/kalimba character (and a different key + tempo) so
DecideDeck does NOT sound like the CoolDecide bot.

Run:  python gen_audio.py   ->  assets/{tick,go,ding,pop,whoosh}.wav + music.mp3
"""
from __future__ import annotations
import os, wave, subprocess
import numpy as np

SR = 44100
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _save_wav(name: str, x: np.ndarray) -> str:
    os.makedirs(ASSETS, exist_ok=True)
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    path = os.path.join(ASSETS, name)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def _env(n, attack=0.004, decay=8.0):
    t = np.linspace(0, n / SR, n, endpoint=False)
    a = np.minimum(1.0, t / attack)
    return a * np.exp(-decay * t)


def _kalimba(freq, dur, amp=0.5, decay=7.0, warmth=0.28):
    """Warm plucked voice: fundamental + soft 2nd harmonic + a touch of vibrato."""
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.5 * t)          # gentle vibrato
    tone = (np.sin(2 * np.pi * freq * t * vib)
            + warmth * np.sin(2 * np.pi * 2 * freq * t)
            + 0.08 * np.sin(2 * np.pi * 3 * freq * t))
    return amp * tone * _env(n, 0.004, decay)


def _lowpass(x, cutoff=3400.0):
    n = max(2, int(SR / cutoff))
    k = np.hanning(n * 2 + 1); k /= k.sum()
    return np.convolve(x, k, mode="same")


# ------------------------- SFX -----------------------------------------------
def make_tick():
    # warm woodblock countdown blip (lower + rounder than CoolDecide's 880Hz)
    s = _kalimba(560, 0.11, amp=0.6, decay=34, warmth=0.15)
    return _save_wav("tick.wav", s)


def make_go():
    # brighter blip for the "1 -> reveal" hand-off
    s = _kalimba(760, 0.12, amp=0.62, decay=30, warmth=0.15)
    return _save_wav("go.wav", s)


def make_ding():
    # happy rising major arpeggio on the reveal:  C6 - E6 - G6 (bell-ish)
    notes = [(1046.50, 0.0), (1318.51, 0.10), (1567.98, 0.20)]
    out = np.zeros(int(SR * 0.85))
    for f, off in notes:
        seg = _kalimba(f, 0.6, amp=0.42, decay=6.5, warmth=0.4)
        s = int(SR * off)
        out[s:s + len(seg)] += seg[: len(out) - s]
    return _save_wav("ding.wav", out * 0.9)


def make_pop():
    # short card-flip pop
    s = _kalimba(430, 0.07, amp=0.5, decay=48, warmth=0.1)
    return _save_wav("pop.wav", s)


def make_whoosh():
    # airy sweep for the winner card rising out of the fan
    n = int(SR * 0.35)
    t = np.linspace(0, 0.35, n, endpoint=False)
    noise = np.random.randn(n) * 0.5
    # sweep a bandpass up by amplitude-modulating filtered noise
    filt = _lowpass(noise, 1800)
    env = np.sin(np.pi * t / 0.35) ** 2
    tone = 0.25 * np.sin(2 * np.pi * (300 + 900 * t / 0.35) * t)
    return _save_wav("whoosh.wav", (filt * 0.35 + tone) * env)


# ------------------------- MUSIC BED -----------------------------------------
# Warm, bouncy toy-piano loop in F major pentatonic (distinct key + tempo from
# CoolDecide's C-pentatonic @104bpm). No dissonant interval exists in the scale,
# so a walk through it is always pleasant. ~19s seamless loop.
BPM = 112
BEAT = 60.0 / BPM
BARS, BPBAR = 8, 4

MEL = {"F": 698.46, "G": 783.99, "A": 880.00, "C": 1046.50, "D": 1174.66}
BASS = {"F": 174.61, "D": 146.83, "Bb": 116.54, "C": 130.81}

PATTERN = [
    ("F",  ["F", "A", "C", "A", "F", "A", "C", "D"]),
    ("D",  ["D", "F", "A", "F", "D", "F", "A", "C"]),
    ("Bb", ["F", "G", "A", "C", "A", "G", "F", "G"]),
    ("C",  ["G", "C", "D", "C", "A", "G", "F", "G"]),
]


def build_music() -> np.ndarray:
    total = int(SR * BARS * BPBAR * BEAT) + SR
    buf = np.zeros(total + SR, dtype=np.float64)
    for bar in range(BARS):
        root, notes = PATTERN[bar % len(PATTERN)]
        bar_t = bar * BPBAR * BEAT
        # bass on downbeat — long, quiet, warm
        b = _kalimba(BASS[root], BEAT * 3.2, amp=0.34, decay=2.2, warmth=0.5)
        s = int(bar_t * SR); buf[s:s + len(b)] += b
        # 8th-note melody, accent on-beats
        for i, nm in enumerate(notes):
            at = bar_t + i * (BEAT / 2)
            amp = 0.16 if i % 2 else 0.24
            p = _kalimba(MEL[nm], BEAT * 1.05, amp=amp, decay=5.2, warmth=0.32)
            s = int(at * SR); buf[s:s + len(p)] += p
    loop_len = int(SR * BARS * BPBAR * BEAT)
    tail = buf[loop_len:loop_len + SR].copy()
    out = buf[:loop_len]
    out[:len(tail)] += tail                     # fold ring-out for seamless loop
    out = _lowpass(out, 3200)
    peak = np.max(np.abs(out)) or 1.0
    return (out / peak) * 0.5


def main():
    np.random.seed(7)                           # deterministic whoosh
    for f in (make_tick(), make_go(), make_ding(), make_pop(), make_whoosh()):
        print("wrote", os.path.basename(f))
    audio = build_music()
    wav = os.path.join(ASSETS, "music.wav")
    _save_wav("music.wav", audio)
    mp3 = os.path.join(ASSETS, "music.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", wav, "-b:a", "192k", mp3],
                   capture_output=True)
    os.remove(wav)
    print(f"wrote music.mp3  ({len(audio)/SR:.1f}s seamless loop @ {BPM}bpm)")


if __name__ == "__main__":
    main()
