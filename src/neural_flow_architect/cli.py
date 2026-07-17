"""Command-line interface for Neural Flow Architect."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from neural_flow_architect import __version__
from neural_flow_architect.core.logging import configure_logging
from neural_flow_architect.core.runtime import NeuralFlowRuntime, RuntimeTick
from neural_flow_architect.core.settings import Settings, get_settings

app = typer.Typer(
    name="nfa",
    help="Neural Flow Architect — proactive flow co-pilot for high-bandwidth BCI users.",
    add_completion=False,
)
console = Console()


def _banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Neural Flow Architect[/] "
            f"v{__version__}\n"
            "[dim]Research / assistive software — not a medical device[/]",
            border_style="cyan",
        )
    )


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    configure_logging("DEBUG" if verbose else "INFO")


@app.command()
def version() -> None:
    """Print version."""
    console.print(__version__)


@app.command()
def status() -> None:
    """Show effective configuration and privacy defaults."""
    settings = get_settings()
    _banner()
    table = Table(title="Runtime settings", show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    rows = [
        ("adapter", settings.adapter),
        ("local_only", str(settings.local_only)),
        ("allow_cloud_llm", str(settings.allow_cloud_llm)),
        ("iot_enabled", str(settings.iot_enabled)),
        ("agent_mode", settings.agent_mode),
        ("dry_run", str(settings.dry_run)),
        ("sample_rate_hz", str(settings.sample_rate_hz)),
        ("channels", str(settings.channels)),
        ("api", f"{settings.api_host}:{settings.api_port}"),
        ("data_dir", str(settings.data_dir)),
    ]
    for k, v in rows:
        table.add_row(k, v)
    console.print(table)
    console.print(
        "[dim]Neural data defaults to local processing. "
        "See docs/privacy/PRIVACY_ETHICS.md[/]"
    )


@app.command()
def demo(
    duration: float = typer.Option(20.0, help="Seconds to run"),
    dry_run: bool = typer.Option(False, help="Do not apply effector side effects"),
) -> None:
    """Run a simulator closed-loop demo (no hardware required)."""
    settings = get_settings()
    settings.adapter = "simulator"
    settings.dry_run = dry_run or settings.dry_run
    _banner()
    console.print(
        f"[green]Starting simulator demo[/] for {duration:.0f}s "
        f"(adapter={settings.adapter}, dry_run={settings.dry_run})"
    )
    asyncio.run(_run_live(settings, duration))


@app.command()
def stream(
    adapter: Optional[str] = typer.Option(None, help="simulator|brainflow|neuralink_stub"),
    duration: float = typer.Option(0.0, help="Seconds (0 = until Ctrl+C)"),
    dry_run: bool = typer.Option(False, help="Dry-run agent effectors"),
) -> None:
    """Stream from the configured (or overridden) adapter."""
    settings = get_settings()
    if adapter:
        settings.adapter = adapter  # type: ignore[assignment]
    settings.dry_run = dry_run or settings.dry_run
    _banner()
    dur = duration if duration > 0 else None
    console.print(f"[green]Streaming[/] adapter={settings.adapter}")
    try:
        asyncio.run(_run_live(settings, dur))
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/]")


def _render_tick(tick: RuntimeTick) -> Panel:
    flow = tick.flow
    decision = tick.decision
    text = Text()
    text.append("State: ", style="bold")
    text.append(f"{flow.state.value}", style="cyan")
    text.append(
        f"  eng={flow.engagement:.2f}  conf={flow.confidence:.2f}  "
        f"min={flow.minutes_in_state:.1f}\n"
    )
    text.append("Mode: ", style="bold")
    text.append(f"{decision.mode.value}\n", style="magenta")
    if tick.digital:
        text.append(
            f"Digital: focus={tick.digital.get('focus_enabled')} "
            f"suppress={tick.digital.get('notifications_suppressed')} "
            f"density={tick.digital.get('density')}\n",
            style="dim",
        )
    if decision.explanations:
        text.append("Architect: ", style="bold green")
        text.append(decision.explanations[-1].text + "\n")
    elif decision.results:
        text.append("Actions: ", style="bold")
        text.append(", ".join(r.tool_id for r in decision.results) + "\n")
    else:
        text.append("Architect: idle\n", style="dim")
    return Panel(text, title="Neural Flow Architect", border_style="blue")


async def _run_live(settings: Settings, duration: float | None) -> None:
    runtime = NeuralFlowRuntime(settings)
    latest: list[RuntimeTick] = []

    def on_tick(tick: RuntimeTick) -> None:
        latest.clear()
        latest.append(tick)

    with Live(Panel("Starting…", title="NFA"), console=console, refresh_per_second=4) as live:
        def _update(tick: RuntimeTick) -> None:
            on_tick(tick)
            live.update(_render_tick(tick))

        ticks = await runtime.run(duration_sec=duration, on_tick=_update)
    console.print(f"[dim]Processed {len(ticks)} flow ticks[/]")
    if runtime.last_flow:
        console.print(
            f"Final state: [cyan]{runtime.last_flow.state.value}[/] "
            f"(engagement={runtime.last_flow.engagement:.2f})"
        )


if __name__ == "__main__":
    app()
