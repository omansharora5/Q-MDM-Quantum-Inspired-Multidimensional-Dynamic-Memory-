"""Build the narrated Q-MDM product video from the HTML render and SAPI voiceover."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent.parent / ".work" / "qmdm-video"
FRAMES = WORK / "frames"
VOICE = WORK / "voiceover.wav"
OUTPUT = ROOT / "qmdm-one-memory-every-agent.mp4"
NARRATION = ROOT / "narration.txt"


def ffmpeg_path() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_voiceover() -> None:
    text = NARRATION.read_text(encoding="utf-8").strip()
    escaped = text.replace("'", "''")
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.SelectVoice('Microsoft Zira Desktop'); "
        "$s.Rate=4; $s.Volume=95; "
        "$s.SetOutputToWaveFile('" + str(VOICE).replace("'", "''") + "'); "
        "$s.Speak('" + escaped + "'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True)
    with wave.open(str(VOICE)) as voice:
        if voice.getnframes() / voice.getframerate() > 20:
            raise ValueError("Narration exceeds 20 seconds; shorten it before encoding")


def encode() -> None:
    ffmpeg = ffmpeg_path()
    output_pattern = str(FRAMES / "frame-%04d.png")
    command = [
        ffmpeg, "-y", "-framerate", "24", "-i", output_pattern,
        "-i", str(VOICE), "-t", "20", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-af", "apad", "-shortest", "-movflags", "+faststart", str(OUTPUT),
    ]
    subprocess.run(command, check=True)


def verify() -> dict:
    ffmpeg = ffmpeg_path()
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(OUTPUT), "-progress", "pipe:1", "-f", "null", "-"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    frames = re.findall(r"^frame=(\d+)", result.stdout, re.MULTILINE)
    if not (frames and frames[-1] == "480" and "out_time=00:00:20." in result.stdout
            and re.search(r"Video: h264.*1920x1080.*24 fps", result.stderr) and "Audio: aac" in result.stderr):
        raise RuntimeError("Export must contain 480 frames at 1920x1080/24fps, 20 seconds and AAC audio")
    return {
        "name": "Q-MDM: One memory, every agent",
        "duration_seconds": 20,
        "fps": 24,
        "resolution": "1920x1080",
        "audio": "SAPI Microsoft Zira Desktop voiceover, AAC",
        "video_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "bytes": OUTPUT.stat().st_size,
        "decode_check": "passed",
    }


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    run_voiceover()
    encode()
    report = verify()
    (ROOT / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
