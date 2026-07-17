# BrainFlow adapter guide

Use open EEG hardware **today** while the core stays Neuralink-ready.

## Install

```bash
pip install -e ".[dev]"           # core + tests (file mode works without BrainFlow)
pip install -e ".[brainflow]"     # optional: live boards + synthetic board
```

**File mode does not require the BrainFlow package** — only NumPy.  
Live boards and BrainFlow synthetic board (`board_id=-1`) need `.[brainflow]`.

## First session in ~10 minutes (no hardware)

```bash
# 1) Health-check the open-EEG path (fixture → stream → features → flow)
nfa doctor --brainflow

# 2) Adapter contract (connect → frames → disconnect)
nfa contract --adapter brainflow

# 3) Serve with shipped synthetic CSV (no real neural data)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_FILE=tests/fixtures/synthetic_eeg.csv \
nfa start --with-ui
```

In the companion UI header you should see something like:

`Signal good · live · brainflow · q 0.90 · …`

| Chip | Meaning |
|---|---|
| `brainflow` | Active adapter (not simulator) |
| `q 0.xx` | Quality overall (0–1); fail-safe softens protect when poor |
| `Signal good/degraded/poor` | Coarse quality band for BCI-friendly glanceability |

## Modes

| Mode | Settings | Notes |
|---|---|---|
| **File replay** | `NFA_ADAPTER=brainflow` + `NFA_BRAINFLOW_FILE=…` | CSV (samples×channels) or `.npy` (channels×samples). **No package required.** |
| **Synthetic board** | `NFA_ADAPTER=brainflow` `NFA_BRAINFLOW_BOARD_ID=-1` | Needs `.[brainflow]`; no headset |
| **Live board** | board id + serial port | See [BrainFlow boards](https://brainflow.readthedocs.io/) |

### Common board IDs

| ID | Board | Notes |
|---|---|---|
| `-1` | Synthetic | CI / demos when BrainFlow is installed |
| `0` | Cyton | USB serial |
| `1` | Ganglion | Bluetooth (platform-dependent) |
| `2` | Ganglion | Native / USB variant — check your BrainFlow version |
| `3` | Cyton Daisy | 16 channels |

Always confirm IDs against the BrainFlow docs for your installed version.

## Examples

```bash
# File fixture (CI-safe, no BrainFlow package)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_FILE=tests/fixtures/synthetic_eeg.csv \
nfa serve

# Synthetic board (BrainFlow package)
NFA_ADAPTER=brainflow NFA_BRAINFLOW_BOARD_ID=-1 nfa serve

# Live Cyton example (adjust port)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_BOARD_ID=0 \
NFA_BRAINFLOW_SERIAL_PORT=/dev/cu.usbserial-XXXX \
nfa serve

# OpenBCI Ganglion (example — verify board_id for your BrainFlow version)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_BOARD_ID=2 \
NFA_BRAINFLOW_SERIAL_PORT=/dev/cu.usbmodem-XXXX \
nfa serve
```

## Doctor: what `--brainflow` checks

| Check | Purpose |
|---|---|
| `brainflow_package` | Optional; live boards need it |
| `brainflow_fixture` | Shipped synthetic CSV present |
| `brainflow_file_contract` | Connect → frames → disconnect on file |
| `brainflow_latency_smoke` | Feature→flow p95 ≤ 80 ms guidance |
| `brainflow_runtime_loop` | Short closed-loop ticks on file adapter |
| `brainflow_synthetic_board` | Live synthetic board if package installed |

```bash
nfa doctor --brainflow
```

## Quality & fail-safe

BrainFlow frames carry quality flags (flatline, clipping, dropout).  
Runtime fail-safe limits proactive actions when quality is poor or the stream stalls.  
Companion UI exposes `quality.overall` and the adapter name in the signal chip.

## Latency guidance

See [docs/architecture/LATENCY_BUDGET.md](../architecture/LATENCY_BUDGET.md).

```bash
nfa doctor --brainflow          # includes latency smoke on fixture
nfa bench --channels 8 --iterations 40
```

Open-EEG feature→flow guidance: **p95 ≤ 80 ms** (50 ms features + 20 ms flow).

## Soak / stability

```bash
nfa soak --duration 600   # 10 minutes simulated stream (fast wall clock)
nfa soak --duration 28800 # 8 hours simulated (long-session memory check)
```

## Privacy

- Prefer ephemeral streaming; do not commit recordings.  
- `data/` session summaries are local and gitignored by default.  
- The repo fixture `tests/fixtures/synthetic_eeg.csv` is **synthetic**, not human data.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `BrainFlow is not installed` | Use file mode, or `pip install -e ".[brainflow]"` |
| `file not found` | Use absolute path or run from repo root; `nfa doctor --brainflow` resolves the fixture |
| Stream stalls / Signal poor | Check serial port, battery, and `nfa doctor --brainflow` quality path |
| Live board won’t start | Confirm board id + port; try synthetic `-1` first |

## Tests (maintainers)

```bash
pytest tests/unit/test_brainflow_file.py tests/integration/test_brainflow_pipeline.py -q
nfa contract --adapter brainflow
```
