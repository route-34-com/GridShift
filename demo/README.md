# Demo video and walkthrough tooling

Scripts that record the GridShift product demo video and the screenshots for the product walkthrough PDF. They run against a throwaway local copy of the app with demo accounts, never against production.

## Requirements

- Python packages: `playwright`, `edge-tts`, `numpy` (plus a Playwright Chromium: `python -m playwright install chromium`)
- `ffmpeg` on the PATH
- A working folder for the app copy, frames, audio and output

| Variable | Default | Purpose |
|---|---|---|
| `GRIDSHIFT_DEMO_WORK` | `E:/demos/gridshift` | Working folder; the app copy lives in `app/` inside it |
| `DEV_TOOLS` | `E:/dev-tools` | Python venv, Playwright browsers and model cache used by `reset.sh` |
| `GRIDSHIFT_DEMO_THEME` | `dark` | Theme for `record.py` (`dark` or `light`) |

## Run order

| Step | Command | What it does |
|---|---|---|
| 1 | `bash demo/reset.sh` | Deletes the demo database and caught mail, then starts the mail catcher (port 1125) and the API (port 8100) |
| 2 | `python demo/prepare.py` | Runs the plan once for the figures quoted in the narration, then synthesises every narration line with edge-tts |
| 3 | `python demo/record.py` | Drives the dashboard through the demo story (with `overlay.js` highlights and callouts) and captures timestamped frames |
| 4 | `python demo/assemble.py [out.mp4]` | Combines frames, narration and a generated music bed into the final video with ffmpeg |

For the walkthrough PDF screenshots, run `bash demo/reset.sh`, then `python demo/shots.py [light|dark]`.

## Files

| File | Purpose |
|---|---|
| `scenes.py` | Narration text for every beat of the video |
| `overlay.js` | Highlight ring, dimming and callout bubbles injected into the page while recording |
| `record.py` | The scripted demo story |
| `shots.py` | Page-by-page screenshots for the walkthrough PDF |

The logins in `record.py` and `shots.py` are made-up demo accounts on `*.example` domains, created fresh by each `reset.sh` run.
