# BCI Adapter Layer Design

**Goal:** One stable core contract for neural (and intent) streams so **today’s open tools** and **tomorrow’s high-bandwidth implant SDKs** plug in without rewriting flow detection, agent logic, or privacy layers.

## 1. Why adapters matter

BCI ecosystems fragment by vendor SDK, sampling rate, channel count, and semantic level (raw voltage vs spikes vs decoded intents). Hardcoding BrainFlow or any single vendor into the flow engine would trap the project.

**Rule:** Core packages (`flow`, `agent`, `privacy`) depend only on **normalized types**, never on vendor SDKs.

## 2. Canonical types

```text
SourceKind: simulator | open_eeg | intracortical | intent_api | replay

ChannelLayout:
  names: list[str]
  units: str                 # e.g. uV, a.u., spikes/s
  positions: optional

StreamMetadata:
  source_kind: SourceKind
  sampling_rate_hz: float
  n_channels: int
  layout: ChannelLayout
  vendor: str | None
  device_id_hash: str | None  # never raw serial in logs by default

QualityFlags:
  clipping: bool
  flatline: bool
  high_noise: bool
  dropout: bool
  overall: float              # 0..1

NeuralFrame:
  seq: int
  timestamp_ns: int
  data: FloatArray[n_channels, n_samples]
  quality: QualityFlags

IntentEvent:                  # high-level path (future Neuralink-class)
  seq: int
  timestamp_ns: int
  intent_type: str            # e.g. select, move, pause_agent
  payload: dict
  confidence: float
```

Adapters may emit **frames**, **intents**, or both.

## 3. Protocol

```python
class BCIAdapter(Protocol):
    name: str

    async def connect(self) -> StreamMetadata: ...
    async def disconnect(self) -> None: ...
    def metadata(self) -> StreamMetadata: ...
    async def health(self) -> QualityFlags: ...

    def stream(self) -> AsyncIterator[NeuralFrame]: ...

    # Optional capabilities
    def capabilities(self) -> set[str]:
        """e.g. {'raw_frames', 'intents', 'impedance'}"""
        ...

    def intents(self) -> AsyncIterator[IntentEvent] | None:
        ...
```

Factory:

```python
build_adapter(name: str, settings: Settings) -> BCIAdapter
```

Config selects adapter via `NFA_ADAPTER=simulator|brainflow|neuralink_stub|replay`.

## 4. Implementations

### 4.1 SimulatorAdapter (Phase 0 — default)

- Generates multichannel noise + injected “engagement” latent  
- Deterministic seed for tests  
- Can script state trajectories: low → pre_flow → flow → deep_flow → break  

**Use for:** demos, CI, agent policy development without hardware.

### 4.2 BrainFlowAdapter (Phase 1)

- Wraps [BrainFlow](https://brainflow.org/) boards and streaming board  
- File replay via BrainFlow playback / raw numpy fixtures  
- Maps board IDs → `StreamMetadata`  
- Optional integration notes for community pipelines (e.g. Neural Ninja-style processing) as **external feature plugins**, not hard core deps  

**Use for:** consumer/research EEG today.

### 4.3 ReplayAdapter

- Reads sanitized fixture files from `tests/fixtures/` or user-provided local paths  
- Never ships real clinical data in the public repo  

### 4.4 NeuralinkStubAdapter (Phase 3 readiness)

- Defines the **hoped-for** high-level surface without claiming private API access  
- Emits synthetic high-channel feature frames + example intent events  
- Documents mapping assumptions for when a real SDK/intent API is available:

```text
Vendor high-level intent  → IntentEvent
Vendor feature stream     → NeuralFrame (features-as-channels) or FeatureWindow
Vendor raw (if ever)      → NeuralFrame with explicit consent scope persist_raw
```

When a real integration is possible under license/ToS, implement `NeuralinkAdapter` **beside** the stub; do not break the protocol.

## 5. Feature extraction boundary

Adapters deliver **time series** (or intents).  
`signal.FeatureExtractor` converts windows → model features.

For high-bandwidth devices, adapters may optionally provide **precomputed features** via a parallel interface:

```python
class FeatureSource(Protocol):
    def feature_stream(self) -> AsyncIterator[FeatureWindow]: ...
```

Core accepts either path:

```text
NeuralFrame → FeatureExtractor → FeatureWindow
                or
FeatureSource → FeatureWindow
```

## 6. Migration path (open tools → implant-class)

| Stage | Signal reality | Adapter | Core changes |
|---|---|---|---|
| Day 1 | Simulated | `simulator` | none |
| MVP | EEG / open boards | `brainflow` | tune features, quality |
| Research | Higher-density open systems | new adapter file | maybe features |
| Production implant | Vendor intent + features | `neuralink` / vendor | personalization scale-up |

**Promise to contributors:** swapping adapters does not require rewriting `Architect` tools or privacy consent model.

## 7. Quality & degradation

Adapters must populate `QualityFlags`. Flow engine uses them to:

- Down-weight estimates  
- Freeze personalization updates  
- Restrict agent to low-impact or idle  

## 8. Security & privacy notes

- Device identifiers hashed before logging  
- Raw frames stay in memory ring buffer unless `persist_raw` consent  
- Adapters must not open network sockets to vendor clouds unless user enables and consent covers it  

## 9. Testing adapters

| Test | How |
|---|---|
| Contract test | All adapters satisfy protocol suite |
| Timing | Simulator under load |
| Replay determinism | Same fixture → same features |
| Disconnect | Clean cancellation |

## 10. Adding a new adapter (checklist)

1. Create `adapters/my_device.py`  
2. Implement protocol  
3. Register in `adapters/registry.py`  
4. Add unit tests with synthetic data  
5. Document channel semantics and sampling  
6. Note privacy considerations  
7. Add example config snippet  

## 11. Related community tooling

The prototype path may compose with community projects for acquisition/visualization (BrainFlow, LabStreamingLayer, open EEG GUIs, research toolkits). Prefer:

- Adapter or sidecar integration  
- Documented optional extras in `pyproject.toml`  
- No mandatory GUI dependency in core library  
