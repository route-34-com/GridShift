"""Pre-run the plan for narration figures, then synthesise every narration line."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import edge_tts

HERE = Path(__file__).parent
WORK = Path(os.environ.get("GRIDSHIFT_DEMO_WORK", "E:/demos/gridshift"))
APP = WORK / "app"
AUDIO = WORK / "voice"
VOICE = "en-US-AndrewNeural"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(HERE))

from scenes import lines  # noqa: E402


def figures() -> dict:
    from backend.datasets import resolve
    from backend.pipeline import run_plan
    from backend.settings import load_settings
    from backend.store import Store

    scratch = WORK / "prerun.db"
    scratch.unlink(missing_ok=True)
    os.chdir(APP)
    data = resolve(load_settings(), Store(scratch))
    plan = run_plan(data.settings, data.store)
    machine = {m["id"]: m for m in plan["machines"]}
    summary = plan["summary"]
    return {
        "savings_eur": summary["savings_eur"],
        "savings_pct": summary["savings_pct"],
        "order": machine["cem-iii-order"]["avg_price"],
        "order_base": machine["cem-iii-order"]["baseline_avg_price"],
        "mill": machine["cement-mill-1"]["avg_price"],
        "mill_base": machine["cement-mill-1"]["baseline_avg_price"],
        "renewable_share": summary["optimized"]["renewable_share"],
        "peak_record_kw": summary["peak"]["record_kw"],
        "peak_planned_kw": summary["optimized"]["peak_import_kw"],
        "peak_rate": summary["peak"]["charge_eur_per_kw_year"],
        "sources": plan["sources"],
    }


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


async def speak(key: str, text: str) -> None:
    target = AUDIO / f"{key}.mp3"
    await edge_tts.Communicate(text, VOICE, rate="-2%").save(str(target))


async def main() -> None:
    AUDIO.mkdir(exist_ok=True)
    numbers = figures()
    print(numbers)
    texts = lines(numbers)
    await asyncio.gather(*(speak(k, t) for k, t in texts.items()))
    meta = {k: {"text": t, "dur": round(duration(AUDIO / f"{k}.mp3"), 2)} for k, t in texts.items()}
    (WORK / "narration.json").write_text(json.dumps({"figures": numbers, "lines": meta}, indent=1), encoding="utf-8")
    print(f"{len(meta)} lines, {sum(m['dur'] for m in meta.values()):.0f}s of speech")


if __name__ == "__main__":
    asyncio.run(main())
