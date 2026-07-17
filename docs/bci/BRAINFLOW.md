# BrainFlow adapter guide

Use open EEG hardware **today** while the core stays Neuralink-ready.

## Install

```bash
pip install -e ".[brainflow]"
```

## Modes

| Mode | Settings | Notes |
|---|---|---|
| **Synthetic board** (no hardware) | `NFA_ADAPTER=brainflow` `NFA_BRAINFLOW_BOARD_ID=-1` | Best for demos/CI when BrainFlow is installed |
| **Live board** | board id + serial port | See [BrainFlow boards](https://brainflow.readthedocs.io/) |
| **File replay** | `NFA_BRAINFLOW_FILE=path/to.csv` | CSV (samples×channels) or `.npy` (channels×samples). **No real neural data in this repo.** |

## Examples

```bash
# Synthetic (no headset)
NFA_ADAPTER=brainflow NFA_BRAINFLOW_BOARD_ID=-1 nfa serve

# File fixture (synthetic CSV shipped for tests)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_FILE=tests/fixtures/synthetic_eeg.csv \
nfa serve

# Live Cyton example (adjust port)
NFA_ADAPTER=brainflow \
NFA_BRAINFLOW_BOARD_ID=0 \
NFA_BRAINFLOW_SERIAL_PORT=/dev/cu.usbserial-XXXX \
nfa serve
```

## Quality & fail-safe

BrainFlow frames carry quality flags (flatline, clipping, dropout).  
Runtime fail-safe limits proactive actions when quality is poor or the stream stalls.

## Privacy

- Prefer ephemeral streaming; do not commit recordings.  
- `data/` session summaries are local and gitignored by default.  
