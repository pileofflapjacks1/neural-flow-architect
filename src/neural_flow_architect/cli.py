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
def doctor() -> None:
    """Check install health (Python, deps, data dir, privacy defaults)."""
    from neural_flow_architect.core.doctor import run_doctor

    _banner()
    report = run_doctor()
    table = Table(title="Doctor", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("OK")
    table.add_column("Detail")
    for c in report.checks:
        table.add_row(c.name, "✓" if c.ok else "✗", c.detail)
    console.print(table)
    if report.ok:
        console.print("[green]All checks passed.[/] Next: [bold]nfa start[/]")
    else:
        console.print("[yellow]Some checks failed.[/] See docs/ux/USER_GUIDE.md")
        raise typer.Exit(code=1)


@app.command()
def start(
    adapter: str = typer.Option("simulator", help="simulator|replay|neuralink_stub|brainflow"),
    host: Optional[str] = typer.Option(None, help="API host"),
    port: Optional[int] = typer.Option(None, help="API port"),
    open_browser: bool = typer.Option(False, "--open/--no-open", help="Open companion UI URL"),
    with_ui: bool = typer.Option(
        False, "--with-ui/--no-with-ui", help="Also launch Vite companion UI if npm is available"
    ),
) -> None:
    """
    Easy daily launcher: local API + clear next steps for BCI users/caregivers.
    """
    import shutil
    import subprocess
    from pathlib import Path

    import uvicorn

    from neural_flow_architect.api.server import create_app

    settings = get_settings()
    settings.adapter = adapter  # type: ignore[assignment]
    if host:
        settings.api_host = host
    if port:
        settings.api_port = port

    ui_proc: subprocess.Popen[str] | None = None
    repo_root = Path(__file__).resolve().parents[2]
    frontend_dir = repo_root / "frontend"

    _banner()
    ui_hint = (
        "Companion UI launching via npm (if available)…"
        if with_ui
        else "2. In another terminal: [cyan]cd frontend && npm run dev[/]"
    )
    console.print(
        Panel(
            "[bold]Easy start for daily use[/]\n\n"
            f"1. API is starting at [cyan]http://{settings.api_host}:{settings.api_port}[/]\n"
            f"{ui_hint}\n"
            "3. Open [cyan]http://127.0.0.1:5173[/]\n"
            "4. Complete onboarding → pick a preset → Start session\n\n"
            "[bold]Shortcuts:[/] P pause · U undo · R rest · S start · Y/N labels\n"
            "[dim]Always available: Pause · Undo · Rest[/]\n"
            "[dim]User guide: docs/ux/USER_GUIDE.md · Caregiver: docs/ux/CAREGIVER_SETUP.md[/]\n"
            "[dim]Not a medical device. Local-first by default.[/]",
            border_style="green",
            title="Neural Flow Architect",
        )
    )
    console.print(f"[green]Adapter:[/] {settings.adapter}")

    if with_ui and shutil.which("npm") and (frontend_dir / "package.json").exists():
        console.print("[green]Starting companion UI…[/]")
        ui_proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=str(frontend_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    elif with_ui:
        console.print("[yellow]--with-ui requested but npm/frontend not ready; API only.[/]")

    if open_browser or with_ui:
        import webbrowser

        webbrowser.open("http://127.0.0.1:5173")

    def _cleanup() -> None:
        if ui_proc is not None and ui_proc.poll() is None:
            ui_proc.terminate()
            try:
                ui_proc.wait(timeout=3)
            except Exception:
                ui_proc.kill()

    app_instance = create_app(settings)
    try:
        uvicorn.run(
            app_instance,
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/]")
    finally:
        _cleanup()


@app.command()
def demo(
    duration: float = typer.Option(20.0, help="Seconds to run"),
    dry_run: bool = typer.Option(False, help="Do not apply effector side effects"),
    adapter: str = typer.Option("simulator", help="simulator|replay"),
) -> None:
    """Run a closed-loop demo (no hardware required)."""
    settings = get_settings()
    settings.adapter = adapter  # type: ignore[assignment]
    settings.dry_run = dry_run or settings.dry_run
    _banner()
    console.print(
        f"[green]Starting demo[/] for {duration:.0f}s "
        f"(adapter={settings.adapter}, dry_run={settings.dry_run})"
    )
    asyncio.run(_run_live(settings, duration))


@app.command()
def stream(
    adapter: Optional[str] = typer.Option(
        None, help="simulator|replay|brainflow|neuralink_stub"
    ),
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


@app.command()
def bench(
    channels: int = typer.Option(8, help="Channel count for stress test"),
    iterations: int = typer.Option(40, help="Timed iterations"),
    sample_rate: float = typer.Option(250.0, help="Sample rate Hz"),
) -> None:
    """Measure feature/flow/agent latency vs documented budgets."""
    from neural_flow_architect.eval.latency import run_latency_bench

    _banner()
    console.print(
        f"[green]Latency bench[/] channels={channels} iterations={iterations}"
    )

    async def _run():
        return await run_latency_bench(
            n_channels=channels,
            iterations=iterations,
            sample_rate_hz=sample_rate,
        )

    report = asyncio.run(_run())
    data = report.to_dict()
    table = Table(title="Latency (ms)", show_header=True, header_style="bold")
    table.add_column("Stage")
    table.add_column("p50")
    table.add_column("p95")
    table.add_column("Budget")
    table.add_column("Pass")
    for stage, stats in data["stages_ms"].items():
        budget = data["budgets_ms"].get(stage, "—")
        ok = data["pass"].get(stage, False)
        table.add_row(
            stage,
            f"{stats['p50']:.2f}",
            f"{stats['p95']:.2f}",
            str(budget),
            "✓" if ok else "✗",
        )
    console.print(table)
    console.print(
        f"[dim]all_pass={data['all_pass']} n_channels={data['n_channels']}[/]"
    )
    console.print("[dim]See docs/architecture/LATENCY_BUDGET.md[/]")


@app.command("eval")
def eval_cmd(
    duration: float = typer.Option(20.0, help="Simulated seconds of offline replay"),
    recipe: str = typer.Option("study", help="Environment recipe context"),
    trajectory: Optional[str] = typer.Option(None, help="Path to trajectory JSON"),
) -> None:
    """Run offline evaluation harness (no server/hardware)."""
    from pathlib import Path

    from neural_flow_architect.eval.harness import run_offline_eval_sync

    _banner()
    console.print(f"[green]Offline eval[/] duration={duration}s recipe={recipe}")
    report = run_offline_eval_sync(
        trajectory_path=Path(trajectory) if trajectory else None,
        duration_sec=duration,
        recipe=recipe,
        dry_run=True,
    )
    data = report.to_dict()
    table = Table(title="Eval report", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    for key in (
        "ticks",
        "mean_engagement",
        "mean_confidence",
        "protect_ticks",
        "degraded_ticks",
        "action_rate",
    ):
        table.add_row(key, str(data.get(key)))
    console.print(table)
    console.print(f"[dim]states={data.get('state_counts')}[/]")
    console.print(f"[dim]modes={data.get('modes')}[/]")
    console.print(f"[dim]actions={data.get('actions')}[/]")


@app.command()
def serve(
    host: Optional[str] = typer.Option(None, help="Bind host (default 127.0.0.1)"),
    port: Optional[int] = typer.Option(None, help="Bind port (default 8741)"),
    adapter: str = typer.Option("simulator", help="simulator|replay|brainflow|neuralink_stub"),
    dry_run: bool = typer.Option(False, help="Dry-run agent effectors"),
) -> None:
    """Start the local companion API (REST + WebSocket)."""
    import uvicorn

    from neural_flow_architect.api.server import create_app

    settings = get_settings()
    settings.adapter = adapter  # type: ignore[assignment]
    settings.dry_run = dry_run or settings.dry_run
    if host:
        settings.api_host = host
    if port:
        settings.api_port = port

    _banner()
    console.print(
        f"[green]Serving[/] http://{settings.api_host}:{settings.api_port}\n"
        f"  WebSocket: ws://{settings.api_host}:{settings.api_port}/ws/state\n"
        f"  Adapter: {settings.adapter}\n"
        "[dim]Bound to localhost by default. Not a medical device.[/]"
    )
    app_instance = create_app(settings)
    uvicorn.run(
        app_instance,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


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

    with Live(Panel("Starting…", title="NFA"), console=console, refresh_per_second=4) as live:

        def _update(tick: RuntimeTick) -> None:
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
