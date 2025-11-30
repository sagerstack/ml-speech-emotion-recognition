"""
Real Inference Integration for Speech Emotion Recognition

This module provides integration between the real backend API and the existing
Streamlit application interface, maintaining compatibility with the AnalysisResult
format expected by the UI components.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from api_client import EmotionAnalysisResult, analyze_emotion, get_api_client
from mock_inference import AnalysisResult

# Configure logging
logger = logging.getLogger(__name__)


class RealSpeechEmotionLab:
    """
    Real inference service that integrates with the backend API
    while maintaining compatibility with the existing UI interface.
    """

    EMOTIONS = ["angry", "disgust", "fearful", "happy", "neutral", "sad", "surprised", "calm"]

    def __init__(self):
        """Initialize the real inference lab."""
        self.api_client = get_api_client()

    def analyze(self, source: str, engine: str = "local") -> AnalysisResult:
        """
        Analyze audio using the real backend API and convert to AnalysisResult format.

        Args:
            source: Path to audio file or file-like object
            engine: Processing engine (local, sagemaker_prod, dual_stack)

        Returns:
            AnalysisResult: Formatted result compatible with existing UI
        """
        try:
            # Handle different input types
            if hasattr(source, 'read'):
                # File-like object (from file upload)
                audio_file = source
                filename = getattr(source, 'name', 'audio_file.wav')
            else:
                # File path string
                audio_file = open(source, 'rb')
                filename = str(source)
                should_close = True

            try:
                logger.info(f"Analyzing audio: {filename} with engine: {engine}")

                # Use the new local endpoint for local engine
                if engine == "local":
                    from api_client import get_api_client
                    api_client = get_api_client()
                    analysis_result = api_client.analyze_audio_local(audio_file, filename)
                else:
                    # Use the old endpoint for sagemaker/dual_stack
                    real_result = analyze_emotion(audio_file, filename, engine)
                    # Convert to AnalysisResult format
                    analysis_result = self._convert_to_analysis_result(real_result, source, engine)

                logger.info(f"Analysis completed: {analysis_result.emotion} ({analysis_result.confidence:.2%})")
                return analysis_result

            finally:
                if 'should_close' in locals() and should_close:
                    audio_file.close()

        except Exception as e:
            logger.error(f"Analysis failed for {source}: {str(e)}")
            # Return a fallback result or re-raise based on your preference
            raise RuntimeError(f"Failed to analyze audio: {str(e)}")

    def _convert_to_analysis_result(
        self,
        real_result: EmotionAnalysisResult,
        source: str,
        engine: str
    ) -> AnalysisResult:
        """
        Convert real API result to AnalysisResult format.

        Args:
            real_result: Result from real API
            source: Original source identifier
            engine: Engine used for analysis

        Returns:
            AnalysisResult: Converted result
        """
        # Create timeline with real metadata
        timeline = self._make_timeline_with_metadata(real_result)

        # Create visualizations (reuse mock for now since real API doesn't provide them)
        visuals = self._make_visualizations_for_emotion(real_result.emotion)

        # Create feature tracks (reuse mock with some real influence)
        feature_tracks = self._make_feature_tracks_for_result(real_result)

        # Create latency breakdown from real metadata
        latency_breakdown = self._create_latency_breakdown(real_result)

        return AnalysisResult(
            source=real_result.source,
            engine=real_result.engine,
            emotion=real_result.emotion,
            confidence=real_result.confidence,
            probabilities=real_result.probabilities,
            processing_time=real_result.processing_time,
            latency_breakdown=latency_breakdown,
            feature_tracks=feature_tracks,
            timeline=timeline,
            visualizations=visuals,
        )

    def _make_timeline_with_metadata(self, real_result: EmotionAnalysisResult) -> List[Dict[str, str]]:
        """Create timeline with real processing metadata."""
        phases = [
            ("Upload & Validation", f"File uploaded: {real_result.source}", "00:00"),
        ]

        # Add backend processing phases if metadata is available
        if real_result.inference_metadata:
            inference_time = real_result.inference_metadata.invocation_time_seconds
            endpoint = real_result.inference_metadata.sagemaker_endpoint

            phases.extend([
                ("Feature Extraction", "Audio features computed", f"00:{inference_time * 0.3:.1f}"),
                ("SageMaker Inference", f"Endpoint: {endpoint.split('-')[-1]}", f"00:{inference_time * 0.7:.1f}"),
                ("Post-Processing", f"Response processed: {real_result.inference_metadata.response_size_bytes} bytes", f"00:{inference_time:.1f}"),
            ])
        else:
            # Fallback timeline
            phases.extend([
                ("Feature Extraction", "Audio features computed", "00:01"),
                ("Model Inference", "Emotion classification", "00:02"),
                ("Post-Processing", "Confidence smoothing applied", "00:03"),
            ])

        return [{"phase": p, "notes": n, "timestamp": t} for p, n, t in phases]

    def _make_visualizations_for_emotion(self, emotion: str) -> Dict[str, np.ndarray]:
        """Create visualizations influenced by the detected emotion."""
        # Create a deterministic seed based on emotion
        emotion_seed = hash(emotion) % (2**32)
        rng = np.random.default_rng(emotion_seed)

        # Adjust visualizations based on emotion characteristics
        base_visuals = {
            "spectrogram": rng.random((64, 96)),
            "mfcc": rng.normal(size=(20, 64)),
            "mel": rng.random((40, 96)),
            "chroma": rng.random((12, 96)),
            "waveform": rng.normal(size=512),
            "temporal_envelope": np.abs(np.sin(np.linspace(0, math.pi * 2, 256))),
        }

        # Apply emotion-specific modifications
        if emotion in ["happy", "surprised"]:
            # Higher energy emotions - more variation
            base_visuals["waveform"] *= 1.5
        elif emotion in ["sad", "calm", "neutral"]:
            # Lower energy emotions - smoother waveforms
            base_visuals["waveform"] *= 0.7
        elif emotion in ["angry", "fearful"]:
            # High arousal emotions - more high frequency content
            base_visuals["spectrogram"][20:, :] *= 1.3

        return base_visuals

    def _make_feature_tracks_for_result(self, real_result: EmotionAnalysisResult) -> pd.DataFrame:
        """Create feature tracks influenced by real analysis results."""
        # Base features
        features = [
            ("RMS Energy", "dB"),
            ("Spectral Centroid", "Hz"),
            ("Zero Crossing", "%"),
            ("Pitch Mean", "Hz"),
            ("MFCC Spread", "std"),
            ("Confidence", "%"),
            ("Processing Time", "s"),
        ]

        # Create deterministic variations based on results
        result_hash = hash(f"{real_result.emotion}-{real_result.confidence}") % (2**32)
        rng = np.random.default_rng(result_hash)

        rows = []
        for name, unit in features:
            if name == "Confidence":
                value = real_result.confidence * 100
                status = "High" if real_result.confidence > 0.8 else "Medium" if real_result.confidence > 0.6 else "Low"
            elif name == "Processing Time":
                value = real_result.processing_time
                status = "Fast" if real_result.processing_time < 2 else "Medium" if real_result.processing_time < 5 else "Slow"
            else:
                # Generate values influenced by the detected emotion
                base_value = rng.uniform(0.2, 0.95)

                # Adjust based on emotion characteristics
                if real_result.emotion in ["happy", "surprised"]:
                    base_value *= 1.1  # Higher energy
                elif real_result.emotion in ["sad", "calm"]:
                    base_value *= 0.9  # Lower energy

                value = round(min(max(base_value, 0.1), 0.99), 3)
                status = rng.choice(["Stable", "Rising", "Falling"])

            rows.append({
                "Feature": name,
                "Value": value,
                "Unit": unit,
                "Status": status,
            })

        return pd.DataFrame(rows)

    def _create_latency_breakdown(self, real_result: EmotionAnalysisResult) -> Dict[str, float]:
        """Create latency breakdown from real metadata."""
        if real_result.inference_metadata:
            # Use real inference time and distribute among phases
            inference_time = real_result.inference_metadata.invocation_time_seconds

            return {
                "upload": 0.1,  # Estimate for upload time
                "feature": inference_time * 0.3,  # Feature extraction portion
                "inference": inference_time * 0.6,  # Actual model inference
                "post_process": inference_time * 0.1,  # Post-processing
            }
        else:
            # Fallback breakdown
            total_time = real_result.processing_time
            return {
                "upload": total_time * 0.1,
                "feature": total_time * 0.35,
                "inference": total_time * 0.45,
                "post_process": total_time * 0.1,
            }

    def health_check(self) -> bool:
        """Check if the backend API is healthy."""
        try:
            return self.api_client.health_check()
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False


# Create global instance
real_lab_backend = RealSpeechEmotionLab()


def get_backend_health() -> bool:
    """
    Check if the real backend is healthy and accessible.

    Returns:
        bool: True if backend is healthy, False otherwise
    """
    return real_lab_backend.health_check()


# For backward compatibility, also provide a mock backend
from mock_inference import MockSpeechEmotionLab
mock_lab_backend = MockSpeechEmotionLab()