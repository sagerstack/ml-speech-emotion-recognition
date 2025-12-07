from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import uuid

import numpy as np
import pandas as pd


@dataclass
class AnalysisResult:
    source: str
    engine: str
    emotion: str
    confidence: float
    probabilities: Dict[str, float]
    processing_time: float
    latency_breakdown: Dict[str, float]
    feature_tracks: pd.DataFrame
    timeline: List[Dict[str, str]]
    visualizations: Dict[str, np.ndarray]
    prediction_id: Optional[str] = None


class MockSpeechEmotionLab:
    """Mock inference + visualization generator used by Streamlit concept apps."""

    EMOTIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgust", "surprised"]

    def analyze(self, source: str, engine: str = "local") -> AnalysisResult:
        rng = self._rng(f"{source}-{engine}-{datetime.utcnow().isoformat(timespec='seconds')}")
        probabilities = rng.random(len(self.EMOTIONS))
        probabilities = probabilities / probabilities.sum()
        emotion_index = probabilities.argmax()
        latency_breakdown = {
            "ingest": float(rng.uniform(0.2, 0.5)),
            "feature": float(rng.uniform(0.35, 0.9)),
            "inference": float(rng.uniform(0.3, 0.8)),
        }
        visuals = self._make_visualizations(rng.integers(0, 10000))
        feature_tracks = self._make_feature_tracks(rng)
        timeline = self._make_timeline()
        prediction_id = str(uuid.uuid4())

        return AnalysisResult(
            source=source,
            engine=engine,
            emotion=self.EMOTIONS[emotion_index],
            confidence=float(probabilities[emotion_index]),
            probabilities=dict(zip(self.EMOTIONS, probabilities)),
            processing_time=float(sum(latency_breakdown.values()) + rng.uniform(0.2, 0.6)),
            latency_breakdown=latency_breakdown,
            feature_tracks=feature_tracks,
            timeline=timeline,
            visualizations=visuals,
            prediction_id=prediction_id,
        )

    def _rng(self, token: str) -> np.random.Generator:
        return np.random.default_rng(abs(hash(token)) % (2**32))

    def _make_feature_tracks(self, rng: np.random.Generator) -> pd.DataFrame:
        features = [
            ("RMS Energy", "dB"),
            ("Spectral Centroid", "Hz"),
            ("Zero Crossing", "%"),
            ("Pitch Mean", "Hz"),
            ("MFCC Spread", "std"),
        ]
        rows = []
        for name, unit in features:
            rows.append(
                {
                    "Feature": name,
                    "Value": round(float(rng.uniform(0.2, 0.95)), 3),
                    "Unit": unit,
                    "Status": rng.choice(["Stable", "Rising", "Falling"]),
                }
            )
        return pd.DataFrame(rows)

    def _make_timeline(self) -> List[Dict[str, str]]:
        phases = [
            ("Acquisition", "Signal normalized", "00:00"),
            ("Feature Stack", "MFCC + Mel computed", "00:02"),
            ("Inference", "Emotion logits produced", "00:03"),
            ("Post-Process", "Confidence smoothing applied", "00:04"),
        ]
        return [{"phase": p, "notes": n, "timestamp": t} for p, n, t in phases]

    def _make_visualizations(self, seed: int) -> Dict[str, np.ndarray]:
        rng = np.random.default_rng(seed)
        return {
            "spectrogram": rng.random((64, 96)),
            "mfcc": rng.normal(size=(20, 64)),
            "mel": rng.random((40, 96)),
            "chroma": rng.random((12, 96)),
            "waveform": rng.normal(size=512),
            "temporal_envelope": np.abs(np.sin(np.linspace(0, math.pi * 2, 256))),
        }


lab_backend = MockSpeechEmotionLab()
