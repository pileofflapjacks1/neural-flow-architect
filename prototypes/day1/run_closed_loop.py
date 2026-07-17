#!/usr/bin/env python3
"""Day-1 minimal closed loop without Rich Live UI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running without install when PYTHONPATH includes src
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from neural_flow_architect.core.runtime import NeuralFlowRuntime  # noqa: E402
from neural_flow_architect.core.settings import Settings  # noqa: E402


async def main() -> None:
    settings = Settings(adapter="simulator", dry_run=True)
    runtime = NeuralFlowRuntime(settings)

    def on_tick(tick):  # type: ignore[no-untyped-def]
        f = tick.flow
        mode = tick.decision.mode.value
        exp = tick.decision.explanations[-1].text if tick.decision.explanations else "-"
        print(
            f"[{f.state.value:10}] eng={f.engagement:.2f} conf={f.confidence:.2f} "
            f"mode={mode:14} | {exp[:80]}"
        )

    ticks = await runtime.run(duration_sec=15, on_tick=on_tick)
    print(f"\nDone. {len(ticks)} ticks.")


if __name__ == "__main__":
    asyncio.run(main())
