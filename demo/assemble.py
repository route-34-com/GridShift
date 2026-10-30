"""Turn captured frames, narration and a generated music bed into the final demo video."""

import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

WORK = Path(os.environ.get("GRIDSHIFT_DEMO_WORK", "E:/demos/gridshift"))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / "GridShift-demo.mp4"
RATE = 48000
VOICE_LEAD = 0.15


def frames_list(timeline: dict) -> float:
    frames, end = timeline["frames"], timeline["end"]
    t0 = frames[0][0]
    lines = []
    for (t, name), nxt in zip(frames, frames[1:] + [(end, None)]):
        lines.append(f"file 'frames/{name}'\nduration {max(0.001, nxt[0] - t):.4f}")
    lines.append(f"file 'frames/{frames[-1][1]}'")
    (WORK / "frames.txt").write_text("\n".join(lines), encoding="utf-8")
    return end - t0


def music(seconds: float, path: Path) -> None:
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[48, 55, 59, 62, 64], [45, 52, 55, 59, 64], [41, 48, 52, 55, 60], [43, 50, 55, 57, 62]]
    span = 8.0
    out = np.zeros((n, 2))
    rng = np.random.default_rng(7)
    for i in range(int(seconds / span) + 2):
        notes = chords[i % len(chords)]
        a, b = int(max(0, (i * span - 1.5) * RATE)), int(min(n, ((i + 1) * span + 2.5) * RATE))
        if a >= n:
            break
        seg = t[a:b] - t[a]
        length = seg[-1] if len(seg) else 1
        env = np.minimum(1, seg / 2.2) * np.minimum(1, (length - seg) / 2.8)
        for k, m in enumerate(notes):
            f = midi(m + 12 if k else m)
            for ch, det in enumerate((-0.9, 0.9)):
                tone = np.sin(2 * np.pi * (f + det) * seg) + 0.18 * np.sin(2 * np.pi * 2 * (f + det) * seg + 0.3)
                out[a:b, ch] += tone * env * (0.5 if k == 0 else 0.2)
        for j in range(int(span)):
            start = int((i * span + j + 0.5) * RATE)
            if start >= n or rng.random() < 0.35:
                continue
            m = notes[rng.integers(1, len(notes))] + 24
            dur = int(2.5 * RATE)
            s = np.arange(min(dur, n - start)) / RATE
            pluck = np.sin(2 * np.pi * midi(m) * s) * np.exp(-s * 2.2) * 0.11
            pan = rng.uniform(0.3, 0.7)
            out[start : start + len(s), 0] += pluck * (1 - pan)
            out[start : start + len(s), 1] += pluck * pan
    fade = np.minimum(1, np.minimum(t / 3, (seconds - t) / 4)).clip(0)[:, None]
    out = out * fade
    out /= np.abs(out).max() + 1e-9
    data = (out * 0.8 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def main() -> None:
    timeline = json.loads((WORK / "timeline.json").read_text(encoding="utf-8"))
    total = frames_list(timeline)
    t0 = timeline["frames"][0][0]
    music(total, WORK / "music.wav")
    marks = [(k, s - t0) for k, s in timeline["marks"]]
    inputs = ["-f", "concat", "-safe", "0", "-i", str(WORK / "frames.txt"), "-i", str(WORK / "music.wav")]
    parts = []
    for i, (key, at) in enumerate(marks):
        inputs += ["-i", str(WORK / "voice" / f"{key}.mp3")]
        ms = int(max(0, at + VOICE_LEAD) * 1000)
        parts.append(f"[{i + 2}:a]aresample={RATE},aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
    mix = "".join(f"[v{i}]" for i in range(len(marks)))
    graph = ";".join(
        parts
        + [
            f"{mix}amix=inputs={len(marks)}:normalize=0,apad=whole_dur={total:.2f}[voice]",
            "[voice]asplit=2[vk][vm]",
            "[1:a]lowpass=f=3200,aecho=0.8:0.6:120|260:0.25|0.18,volume=0.16[bed]",
            "[bed][vk]sidechaincompress=threshold=0.03:ratio=6:attack=80:release=900[ducked]",
            "[vm][ducked]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
            f"[0:v]fps=30,scale=1920:1080:flags=lanczos,format=yuv420p,fade=t=in:d=0.8,fade=t=out:st={total - 1.2:.2f}:d=1.2[vout]",
        ]
    )
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", graph, "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-ar", str(RATE),
           "-t", f"{total:.2f}", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True, cwd=WORK)
    print(f"{OUT} · {total:.1f}s")


if __name__ == "__main__":
    main()
