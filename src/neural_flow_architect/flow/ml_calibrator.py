"""Lightweight hybrid ML calibrator for flow-related engagement.

Uses scikit-learn logistic regression on derived feature proxies + self-report
labels. Never stores raw neural samples. Falls back gracefully when untrained
or sklearn unavailable.

Not a clinical model — research / assistive prototype only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

FEATURE_KEYS = (
    "engagement_proxy",
    "arousal_proxy",
    "self_ref_proxy",
    "ease_proxy",
    "quality_overall",
)


@dataclass
class CalibratorStatus:
    trained: bool
    n_samples: int
    n_positive: int
    model: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trained": self.trained,
            "n_samples": self.n_samples,
            "n_positive": self.n_positive,
            "model": self.model,
            "message": self.message,
        }


def features_to_vector(features: dict[str, float], *, quality_overall: float = 1.0) -> list[float]:
    """Fixed-order feature vector for training / inference."""
    out: list[float] = []
    for key in FEATURE_KEYS:
        if key == "quality_overall":
            out.append(float(features.get(key, quality_overall)))
        else:
            out.append(float(features.get(key, 0.0)))
    return out


class FlowMLCalibrator:
    """
    Binary 'in-flow-like' probability from local labels.

    Trains when both classes are present and n_samples >= min_samples.
    """

    def __init__(
        self,
        *,
        samples_path: Path | None = None,
        min_samples: int = 8,
        blend_weight: float = 0.35,
    ) -> None:
        self.samples_path = samples_path
        self.min_samples = min_samples
        self.blend_weight = float(max(0.0, min(0.8, blend_weight)))
        self._clf: Any | None = None
        self._n_samples = 0
        self._n_positive = 0
        self._model_name = "none"
        if samples_path and samples_path.exists():
            self.retrain_from_disk()

    @property
    def is_ready(self) -> bool:
        return self._clf is not None

    def status(self) -> CalibratorStatus:
        if self._clf is None:
            return CalibratorStatus(
                trained=False,
                n_samples=self._n_samples,
                n_positive=self._n_positive,
                model=self._model_name,
                message=(
                    f"Need ≥{self.min_samples} labeled samples with both classes; "
                    f"have {self._n_samples} (pos={self._n_positive}). Using rules only."
                ),
            )
        return CalibratorStatus(
            trained=True,
            n_samples=self._n_samples,
            n_positive=self._n_positive,
            model=self._model_name,
            message=(
                f"Hybrid ML active ({self._model_name}, n={self._n_samples}). "
                f"Blend weight={self.blend_weight:.2f}."
            ),
        )

    def append_sample(
        self,
        features: dict[str, float],
        *,
        felt_in_flow: bool,
        quality_overall: float = 1.0,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Append one local training sample (JSONL). Does not retrain automatically."""
        if self.samples_path is None:
            return
        self.samples_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "x": features_to_vector(features, quality_overall=quality_overall),
            "y": 1 if felt_in_flow else 0,
            "meta": meta or {},
        }
        with self.samples_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        self._n_samples += 1
        if felt_in_flow:
            self._n_positive += 1

    def load_xy(self) -> tuple[NDArray[np.float64], NDArray[np.int_]]:
        xs: list[list[float]] = []
        ys: list[int] = []
        if self.samples_path is None or not self.samples_path.exists():
            return np.zeros((0, len(FEATURE_KEYS))), np.zeros((0,), dtype=np.int_)
        for line in self.samples_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            x = row.get("x")
            if not isinstance(x, list) or len(x) != len(FEATURE_KEYS):
                continue
            xs.append([float(v) for v in x])
            ys.append(int(row.get("y", 0)))
        if not xs:
            return np.zeros((0, len(FEATURE_KEYS))), np.zeros((0,), dtype=np.int_)
        return np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.int_)

    def retrain_from_disk(self) -> CalibratorStatus:
        """Fit logistic regression if enough balanced labels exist."""
        x, y = self.load_xy()
        self._n_samples = int(x.shape[0])
        self._n_positive = int(np.sum(y == 1)) if self._n_samples else 0
        self._clf = None
        self._model_name = "none"

        if self._n_samples < self.min_samples:
            return self.status()
        if len(set(y.tolist())) < 2:
            return self.status()

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import StandardScaler
        except ImportError:  # pragma: no cover
            self._model_name = "sklearn-missing"
            return self.status()

        pipe: Any = Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                        solver="lbfgs",
                    ),
                ),
            ]
        )
        pipe.fit(x, y)
        self._clf = pipe
        self._model_name = "logreg"
        return self.status()

    def predict_in_flow_proba(
        self, features: dict[str, float], *, quality_overall: float = 1.0
    ) -> float | None:
        """P(in-flow-like). None if untrained."""
        if self._clf is None:
            return None
        vec = np.asarray(
            [features_to_vector(features, quality_overall=quality_overall)],
            dtype=np.float64,
        )
        proba = self._clf.predict_proba(vec)[0]
        # class 1 = in flow
        classes = list(getattr(self._clf, "classes_", [0, 1]))
        if 1 in classes:
            idx = classes.index(1)
            return float(proba[idx])
        return float(proba[-1])

    def blend_engagement(
        self,
        rule_engagement: float,
        features: dict[str, float],
        *,
        quality_overall: float = 1.0,
    ) -> tuple[float, list[str]]:
        """
        Blend rule engagement with ML probability.

        Returns (engagement, reasons).
        """
        reasons: list[str] = []
        p = self.predict_in_flow_proba(features, quality_overall=quality_overall)
        if p is None:
            return rule_engagement, reasons
        w = self.blend_weight
        blended = (1.0 - w) * rule_engagement + w * p
        reasons.append(f"hybrid_ml p_in_flow={p:.3f} w={w:.2f}")
        return float(max(0.0, min(1.0, blended))), reasons

    def train_from_sessions(self, sessions: list[dict[str, Any]]) -> CalibratorStatus:
        """
        Ingest labels from session summaries into the sample store, then retrain.

        Uses engagement_at_label as a 1-D proxy expanded into a feature vector
        when full feature snapshots are not available.
        """
        if self.samples_path is None:
            return self.status()
        added = 0
        for s in sessions:
            for lab in s.get("labels") or []:
                if lab.get("felt_in_flow") is None:
                    continue
                eng = float(lab.get("engagement_at_label") or 0.5)
                # Expand single engagement into a soft feature sketch
                features = {
                    "engagement_proxy": eng,
                    "arousal_proxy": 0.5,
                    "self_ref_proxy": max(0.0, 1.0 - eng * 0.6),
                    "ease_proxy": min(1.0, eng * 0.8 + 0.1),
                    "quality_overall": 0.9,
                }
                # Prefer full snapshot if present
                snap = lab.get("features") or {}
                if isinstance(snap, dict) and snap:
                    for k in FEATURE_KEYS:
                        if k in snap:
                            features[k] = float(snap[k])
                self.append_sample(
                    features,
                    felt_in_flow=bool(lab.get("felt_in_flow")),
                    quality_overall=float(features.get("quality_overall", 0.9)),
                    meta={"session_id": s.get("session_id"), "source": "session_label"},
                )
                added += 1
        if added:
            return self.retrain_from_disk()
        # still try retrain from existing disk samples
        return self.retrain_from_disk()
