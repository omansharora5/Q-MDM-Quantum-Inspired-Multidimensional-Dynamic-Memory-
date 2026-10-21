# Q-MDM: One memory, every agent

This is the 20-second narrated product video for the current project. It is an
illustrated explanation using synthetic examples, not a recording of a live
model session or a benchmark result.

## Storyboard

- 0â€“4s: separate agent chats lose shared decisions.
- 4â€“8s: a source message becomes a shared, versioned memory.
- 8â€“12s: a new plan becomes current while history stays inspectable.
- 12â€“17s: a second agent recalls only connected evidence.
- 17â€“20s: end card and product name.

The animation is authored in `index.html`, `style.css`, and `video.js`.
The final export is `qmdm-one-memory-every-agent.mp4` at 1920Ã—1080, 24fps,
with a Microsoft Zira Desktop narration track.

## Rebuild on Windows

Run from the repository root. The application needs its normal Python environment.
Video export also needs Playwright with Chromium, `imageio-ffmpeg`, and the installed
Microsoft Zira Desktop voice. Video dependencies are separate from the memory service.

```powershell
npm install --no-save --package-lock=false --prefix artifacts/qmdm-video playwright
& .\artifacts\qmdm-video\node_modules\.bin\playwright.cmd install chromium
.\.venv\Scripts\python.exe -m pip install imageio-ffmpeg
node artifacts/qmdm-video/render_frames.cjs
.\.venv\Scripts\python.exe artifacts/qmdm-video/encode_video.py
```

The renderer writes all 480 frames into `.work/qmdm-video/frames`. It rebuilds by
default. Set `QMDM_RESUME=1` only when continuing the same unchanged source; existing
frames are reused and missing frames are filled. `QMDM_END` limits the frame count
for a partial render. Partial renders are not ready for export. `QMDM_PLAYWRIGHT`
can point to an existing Playwright module if you already have one installed.

The encoder checks that narration fits within 20 seconds, then decodes the MP4
and verifies frame count, video dimensions, frame rate, duration and an AAC audio
track before writing `manifest.json`. The manifest's SHA-256 identifies the
finished file. A separate check decoded the current export and measured the
18.12-second narration. A fresh dependency installation and full frame rebuild
were not repeated during this verification.
