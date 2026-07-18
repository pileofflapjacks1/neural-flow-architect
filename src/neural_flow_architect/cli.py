"""Command-line interface for Neural Flow Architect."""

from __future__ import annotations

import asyncio
from typing import Any

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
        "[dim]Neural data defaults to local processing. See docs/privacy/PRIVACY_ETHICS.md[/]"
    )


@app.command()
def soak(
    duration: float = typer.Option(
        300.0, help="Simulated stream seconds (not wall clock; uses fast replay)"
    ),
    channels: int = typer.Option(8, help="Channel count"),
    memory_limit_mb: float = typer.Option(512.0, help="Fail if peak RSS exceeds this"),
) -> None:
    """Long-session soak test (fast-forward) for multi-hour stability."""
    from neural_flow_architect.eval.soak import run_soak_sync

    _banner()
    console.print(f"[green]Soak test[/] simulated_duration={duration}s channels={channels}")
    report = run_soak_sync(
        duration_sec=duration, channels=channels, memory_limit_mb=memory_limit_mb
    )
    data = report.to_dict()
    table = Table(title="Soak report", show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in data.items():
        if k == "notes":
            continue
        table.add_row(k, str(v))
    console.print(table)
    for note in data.get("notes") or []:
        console.print(f"[dim]{note}[/]")
    if not data.get("ok"):
        raise typer.Exit(code=1)


@app.command()
def report(
    data_dir: str | None = typer.Option(None, help="Override data directory"),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    days: int = typer.Option(7, "--days", help="Weekly recap window in days"),
) -> None:
    """Print local trust, policy scoreboard, and weekly recap (no raw neural data)."""
    import json as json_lib
    from pathlib import Path

    from neural_flow_architect.core.session import SessionController

    settings = get_settings()
    if data_dir:
        settings.data_dir = Path(data_dir)
    session = SessionController(settings)
    trust = session.trust_metrics()
    scoreboard = session.policy_scoreboard()
    weekly = session.weekly_recap(days=days)
    sessions = session.list_sessions()
    payload = {
        "trust": trust.get("trust"),
        "scoreboard": scoreboard,
        "weekly": weekly,
        "sessions_on_disk": len(sessions),
        "iot": trust.get("iot"),
        "os_focus": session.runtime.os_focus.status(),
    }
    if as_json:
        console.print_json(json_lib.dumps(payload))
        return

    _banner()
    t = trust.get("trust") or {}
    table = Table(title="Trust report", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    for k in (
        "trust_score",
        "undo_rate",
        "helpful",
        "unhelpful",
        "never",
        "actions_count",
        "undos_count",
        "interpretation",
    ):
        table.add_row(k, str(t.get(k, "—")))
    console.print(table)
    sb = scoreboard
    console.print(f"[cyan]Policy score:[/] {sb.get('score')} — {sb.get('interpretation')}")
    console.print(
        f"[cyan]This week ({weekly.get('window_days')}d):[/] "
        f"sessions={weekly.get('sessions')} score={weekly.get('score')} "
        f"trend={weekly.get('trend')} "
        f"flow_min={(weekly.get('totals') or {}).get('flow_minutes')}"
    )
    for h in (weekly.get("highlights") or [])[:4]:
        console.print(f"  · {h}")
    console.print(f"[dim]Sessions on disk: {len(sessions)}[/]")
    if sessions:
        s0 = sessions[0]
        console.print(
            f"[dim]Latest: {s0.get('session_id', '')[:8]}… "
            f"peak={s0.get('peak_engagement')} flow_min={s0.get('flow_minutes')}[/]"
        )
    console.print(f"[dim]IoT mode: {(trust.get('iot') or {}).get('mode')}[/]")
    console.print(f"[dim]OS Focus: {session.runtime.os_focus.status().get('mode')}[/]")


@app.command("contract")
def contract_cmd(
    adapter: str = typer.Option("simulator", help="simulator|replay|neuralink_stub|brainflow"),
) -> None:
    """Run adapter contract golden suite (connect → frames → disconnect)."""
    from neural_flow_architect.adapters.contract import run_adapter_contract
    from neural_flow_architect.adapters.registry import build_adapter

    settings = get_settings()
    settings.adapter = adapter  # type: ignore[assignment]
    # BrainFlow file mode without package when using synthetic file
    if adapter == "brainflow" and not settings.brainflow_file:
        from neural_flow_architect.adapters.registry import default_brainflow_fixture

        settings.brainflow_file = str(default_brainflow_fixture())
    _banner()
    console.print(f"[green]Adapter contract[/] adapter={adapter}")
    ad = build_adapter(settings)
    report = asyncio.run(run_adapter_contract(ad, max_frames=3))
    table = Table(title="Contract report", show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in report.items():
        table.add_row(k, str(v))
    console.print(table)
    if not report.get("ok"):
        raise typer.Exit(code=1)


@app.command()
def doctor(
    brainflow: bool = typer.Option(
        False,
        "--brainflow",
        help="Also validate open-EEG path: fixture file, file stream, latency, optional package",
    ),
) -> None:
    """Check install health (Python, deps, data dir, privacy defaults)."""
    from neural_flow_architect.core.doctor import run_doctor

    _banner()
    report = run_doctor(brainflow=brainflow)
    title = "Doctor (BrainFlow path)" if brainflow else "Doctor"
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("OK")
    table.add_column("Detail")
    for c in report.checks:
        table.add_row(c.name, "✓" if c.ok else "✗", c.detail)
    console.print(table)
    if report.ok:
        if brainflow:
            console.print(
                "[green]BrainFlow path OK.[/] Try: "
                "[bold]NFA_ADAPTER=brainflow NFA_BRAINFLOW_FILE=tests/fixtures/synthetic_eeg.csv nfa start[/]"
            )
        else:
            console.print(
                "[green]All checks passed.[/] Next: [bold]nfa start[/] "
                "(or [bold]nfa doctor --brainflow[/] for open-EEG path)"
            )
    else:
        console.print(
            "[yellow]Some checks failed.[/] See docs/bci/BRAINFLOW.md and docs/ux/USER_GUIDE.md"
        )
        raise typer.Exit(code=1)


@app.command()
def start(
    adapter: str = typer.Option("simulator", help="simulator|replay|neuralink_stub|brainflow"),
    host: str | None = typer.Option(None, help="API host"),
    port: int | None = typer.Option(None, help="API port"),
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

    ui_proc: subprocess.Popen[bytes] | None = None
    ui_log: Path | None = None
    repo_root = Path(__file__).resolve().parents[2]
    frontend_dir = repo_root / "frontend"
    ui_ready = False

    def _ensure_frontend() -> bool:
        """Install npm deps if needed; return True when Vite can start."""
        nonlocal ui_log
        if not shutil.which("npm"):
            console.print(
                "[yellow]npm not found.[/] Install Node.js, then:\n"
                "  [cyan]cd frontend && npm install && npm run dev[/]"
            )
            return False
        if not (frontend_dir / "package.json").exists():
            console.print(f"[yellow]No frontend at {frontend_dir}[/]")
            return False
        node_modules = frontend_dir / "node_modules"
        if not node_modules.is_dir():
            console.print(
                "[yellow]frontend/node_modules missing — running [bold]npm install[/] "
                "(first time, may take a minute)…[/]"
            )
            install = subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if install.returncode != 0:
                console.print("[red]npm install failed.[/]")
                if install.stderr:
                    console.print(install.stderr[-1500:])
                console.print(
                    "Fix: [cyan]cd frontend && npm install && npm run dev[/] "
                    "then open [cyan]http://127.0.0.1:5173[/]"
                )
                return False
            console.print("[green]npm install complete.[/]")
        return True

    def _start_vite() -> subprocess.Popen[bytes] | None:
        nonlocal ui_log, ui_ready
        ui_log = settings.data_dir / "logs" / "vite-dev.log"
        ui_log.parent.mkdir(parents=True, exist_ok=True)
        log_f = open(ui_log, "w", encoding="utf-8")  # noqa: SIM115
        proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
            cwd=str(frontend_dir),
            stdout=log_f,
            stderr=subprocess.STDOUT,
        )
        # Wait briefly for Vite to bind 5173
        import socket
        import time

        for _ in range(40):
            if proc.poll() is not None:
                log_f.flush()
                tail = ui_log.read_text(encoding="utf-8", errors="replace")[-1200:]
                console.print("[red]Vite exited early.[/] Log tail:")
                console.print(tail or "(empty)")
                console.print(f"[dim]Full log: {ui_log}[/]")
                return None
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex(("127.0.0.1", 5173)) == 0:
                    ui_ready = True
                    console.print(
                        "[green]Companion UI ready:[/] [cyan]http://127.0.0.1:5173[/]\n"
                        f"[dim]Vite log: {ui_log}[/]"
                    )
                    return proc
            time.sleep(0.25)
        console.print(
            "[yellow]Vite still starting…[/] Open [cyan]http://127.0.0.1:5173[/] in a few seconds.\n"
            f"[dim]If blank, check {ui_log}[/]"
        )
        return proc

    _banner()
    console.print(f"[green]Adapter:[/] {settings.adapter}")

    if with_ui:
        if _ensure_frontend():
            console.print("[green]Starting companion UI (Vite on :5173)…[/]")
            ui_proc = _start_vite()
        else:
            console.print("[yellow]--with-ui skipped; API only.[/]")
    else:
        console.print(
            Panel(
                "[bold]API only[/]\n\n"
                f"API: [cyan]http://{settings.api_host}:{settings.api_port}[/]  "
                f"(health: [cyan]/health[/])\n"
                "UI is [bold]not[/] on the API port — run:\n"
                "  [cyan]cd frontend && npm install && npm run dev[/]\n"
                "Then open [cyan]http://127.0.0.1:5173[/]\n\n"
                "Or restart with: [cyan]nfa start --with-ui[/]",
                border_style="cyan",
                title="How to open the companion UI",
            )
        )

    if with_ui and ui_ready:
        console.print(
            Panel(
                "[bold]Daily use[/]\n\n"
                f"• API: [cyan]http://{settings.api_host}:{settings.api_port}/health[/]\n"
                "• UI:  [cyan]http://127.0.0.1:5173[/]  ← open this in the browser\n"
                "• Onboarding → preset → [bold]Start session[/]\n\n"
                "[bold]Shortcuts:[/] P pause · U undo · R rest · S start · Y/N labels\n"
                "[dim]Not a medical device. Local-first by default.[/]",
                border_style="green",
                title="Neural Flow Architect",
            )
        )

    if (open_browser or with_ui) and ui_ready:
        import webbrowser

        webbrowser.open("http://127.0.0.1:5173")
    elif open_browser and not with_ui:
        import webbrowser

        webbrowser.open(f"http://{settings.api_host}:{settings.api_port}/")

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
    adapter: str | None = typer.Option(None, help="simulator|replay|brainflow|neuralink_stub"),
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
    console.print(f"[green]Latency bench[/] channels={channels} iterations={iterations}")

    async def _run() -> Any:
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
    console.print(f"[dim]all_pass={data['all_pass']} n_channels={data['n_channels']}[/]")
    console.print("[dim]See docs/architecture/LATENCY_BUDGET.md[/]")


@app.command("eval")
def eval_cmd(
    duration: float = typer.Option(20.0, help="Simulated seconds of offline replay"),
    recipe: str = typer.Option("study", help="Environment recipe context"),
    trajectory: str | None = typer.Option(None, help="Path to trajectory JSON"),
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
    host: str | None = typer.Option(None, help="Bind host (default 127.0.0.1)"),
    port: int | None = typer.Option(None, help="Bind port (default 8741)"),
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
