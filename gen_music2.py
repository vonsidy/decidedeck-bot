"""DecideDeck music bed — take 2.  A real, bouncy, cheerful loop (not an ambient
drone).  Original + royalty-free (numpy) so it can never trigger a copyright
claim on the monetized channel.

What went wrong before and what's fixed:
  * pure sine + vibrato  -> sounded like a horror music box.  Removed the vibrato;
    use a bright marimba/uke tone with real harmonics.
  * no rhythm            -> added a soft kick + shaker groove so it BOUNCES.
  * notes smeared        -> shorter, plucky decays so each note is distinct.
  * random pentatonic walk -> a clear, happy I-V-vi-IV chord progression that
    resolves, so it always sounds musical.

Run:  python gen_music2.py   -> assets/music_A.mp3  +  assets/music_B.mp3
"""
from __future__ import annotations
import os, wave, subprocess
import numpy as np

SR = 44100
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

NOTE = {  # equal-temperament, Hz
    "G3":196.00,"A3":220.00,"Bb3":233.08,"C4":261.63,"D4":293.66,"E4":329.63,
    "F4":349.23,"G4":392.00,"A4":440.00,"B4":493.88,"C5":523.25,"D5":587.33,
    "E5":659.25,"F5":698.46,"G5":783.99,"A5":880.00,
}
BASSN = {"C2":65.41,"G2":98.00,"A2":110.00,"F2":87.31,"D2":73.42}


def _lowpass(x, cutoff=5200.0):
    n = max(2, int(SR / cutoff)); k = np.hanning(n*2+1); k /= k.sum()
    return np.convolve(x, k, mode="same")


def _mallet(freq, dur, amp, decay, harm):
    """Bright plucked/mallet tone: fixed harmonic stack, fast attack, no vibrato."""
    n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
    tone = sum(a*np.sin(2*np.pi*freq*(i+1)*t) for i, a in enumerate(harm))
    env = np.exp(-decay*t) * np.minimum(1.0, t/0.003)
    return amp*tone*env


def _bass(freq, dur, amp, decay=6.0):
    n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
    tone = np.sin(2*np.pi*freq*t) + 0.30*np.sin(2*np.pi*2*freq*t)
    env = np.exp(-decay*t) * np.minimum(1.0, t/0.004)
    return amp*tone*env


def _kick(amp=0.7, dur=0.17):
    n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
    f = 45 + 95*np.exp(-t*32)                    # pitch drops 140->45 Hz
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)*np.exp(-t*11)
    click = np.exp(-t*240)*0.25
    return amp*(body+click)


def _shaker(amp=0.11, dur=0.055, bright=2600):
    n = int(SR*dur)
    noise = np.random.randn(n)
    hp = noise - _lowpass(noise, bright)         # crude high-pass -> "tss"
    env = np.exp(-np.linspace(0, dur, n)*46)
    return amp*hp*env


def _add(buf, seg, at):
    s = int(at*SR); e = min(len(buf), s+len(seg))
    if s < len(buf): buf[s:e] += seg[:e-s]


def build(cfg) -> np.ndarray:
    bpm = cfg["bpm"]; beat = 60.0/bpm
    bars = cfg["bars"]                            # list of (bassNote, [4 melody notes])
    harm = cfg["harm"]; mdecay = cfg["mdecay"]
    loop_len = int(SR * len(bars)*4*beat)
    buf = np.zeros(loop_len + SR, dtype=np.float64)

    for bi, (broot, mel) in enumerate(bars):
        b0 = bi*4*beat
        # --- bass: root on beats 1 & 3
        _add(buf, _bass(BASSN[broot], beat*1.9, 0.34), b0)
        _add(buf, _bass(BASSN[broot], beat*1.6, 0.24), b0+2*beat)
        # --- kick on beats 1 & 3
        _add(buf, _kick(0.62), b0); _add(buf, _kick(0.5), b0+2*beat)
        # --- shaker on all 8 eighth-notes (accent the offbeats -> bounce)
        for j in range(8):
            a = 0.13 if j % 2 else 0.08
            _add(buf, _shaker(a), b0 + j*(beat/2))
        # --- melody: quarter notes, with a light 8th-note echo on beats 2 & 4
        for j, nm in enumerate(mel):
            acc = 0.30 if j % 2 == 0 else 0.24
            _add(buf, _mallet(NOTE[nm], beat*0.95, acc, mdecay, harm), b0 + j*beat)
            if j in (1, 3):                        # bouncy upbeat echo, quieter+octave
                _add(buf, _mallet(NOTE[nm], beat*0.5, 0.12, mdecay+3, harm), b0 + j*beat + beat/2)

    # Fold the ring-out tail back over the start so looping is SEAMLESS
    # (chopping at loop_len leaves a click/gap at the seam).
    tail = buf[loop_len:loop_len + SR].copy()
    out = buf[:loop_len].copy()
    out[:len(tail)] += tail
    out = _lowpass(out, 5200)
    peak = np.max(np.abs(out)) or 1.0
    return (out/peak)*0.62


def to_mp3(audio, name):
    wav = os.path.join(ASSETS, "_tmp.wav")
    pcm = (np.clip(audio, -1, 1)*32767).astype("<i2")
    with wave.open(wav, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    mp3 = os.path.join(ASSETS, name)
    subprocess.run(["ffmpeg", "-y", "-i", wav, "-b:a", "192k", mp3], capture_output=True)
    os.remove(wav)
    print(f"wrote {name}  ({len(audio)/SR:.1f}s loop)")


# --- Option A: "Marimba Bounce" — warm, rounded, playful. I-V-vi-IV in C. 120bpm
OPT_A = {
    "bpm": 160, "mdecay": 8.5, "harm": [1.0, 0.55, 0.28, 0.10],
    "bars": [
        ("C2", ["C5","E5","G5","E5"]),
        ("G2", ["D5","G5","D5","B4"]),
        ("A2", ["C5","E5","C5","A4"]),
        ("F2", ["F5","C5","A4","C5"]),
        ("C2", ["E5","G5","E5","C5"]),
        ("G2", ["G5","D5","B4","D5"]),
        ("A2", ["A4","C5","E5","C5"]),
        ("F2", ["C5","A4","F4","A4"]),
    ],
}

# --- Option B: "Ukulele Skip" — brighter, pluckier, a touch faster. Same happy
# progression, more harmonics + shorter decay = plucked-string feel. 132bpm
OPT_B = {
    "bpm": 174, "mdecay": 12.0, "harm": [1.0, 0.7, 0.5, 0.28, 0.14],
    "bars": [
        ("C2", ["E5","G5","C5","G5"]),
        ("G2", ["D5","B4","G4","B4"]),
        ("A2", ["E5","C5","A4","C5"]),
        ("F2", ["A4","C5","F5","C5"]),
        ("C2", ["G5","E5","C5","E5"]),
        ("G2", ["B4","D5","G5","D5"]),
        ("A2", ["C5","E5","A5","E5"]),
        ("F2", ["F5","A4","C5","A4"]),
    ],
}

if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    np.random.seed(11)
    to_mp3(build(OPT_A), "music_A.mp3")
    np.random.seed(12)
    to_mp3(build(OPT_B), "music_B.mp3")
