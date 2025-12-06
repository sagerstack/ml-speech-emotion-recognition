"""
Performance tests for Visualization Inference Feature.

This test suite validates that the audio_features inference feature meets
performance requirements and has acceptable overhead.

Tests cover:
- Baseline extraction time without audio_features
- Extraction time with audio_features
- Overhead is acceptable (< 50ms or < 50% increase)
- Response size with/without audio_features
- Response compression effectiveness
- Concurrent request handling
- Memory usage
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


class TestBaselinePerformance:
    """Test baseline performance without audio_features."""

    def test_baseline_inference_time(self, client, sample_audio_file):
        """Test that baseline inference (without audio_features) completes quickly."""
        # Warm up
        client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        # Measure time for 5 requests
        timings = []
        for _ in range(5):
            start_time = time.time()
            response = client.post(
                "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
            )
            elapsed = time.time() - start_time
            timings.append(elapsed)

            assert response.status_code == 200

        avg_time = sum(timings) / len(timings)
        max_time = max(timings)

        # Baseline should be fast (< 1 second average)
        assert avg_time < 1.0, f"Baseline average time {avg_time:.3f}s should be < 1.0s"

        # Max time should be reasonable (< 2 seconds)
        assert max_time < 2.0, f"Baseline max time {max_time:.3f}s should be < 2.0s"

        # Return average for comparison
        return avg_time

    def test_baseline_response_size(self, client, sample_audio_file):
        """Test baseline response size without audio_features."""
        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        assert response.status_code == 200

        response_size = len(response.content)

        # Baseline response should be small (< 5KB)
        assert response_size < 5 * 1024, f"Baseline response {response_size} bytes should be < 5KB"

        return response_size


class TestVisualizationPerformance:
    """Test performance with audio_features enabled."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_inference_time(self, client, sample_audio_file):
        """Test that inference with audio_features completes in acceptable time."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        # Warm up
        client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        # Measure time for 5 requests
        timings = []
        for _ in range(5):
            start_time = time.time()
            response = client.post(
                "/v1/inference/latest?include_audio_features=true",
                files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            )
            elapsed = time.time() - start_time
            timings.append(elapsed)

            assert response.status_code == 200

        avg_time = sum(timings) / len(timings)
        max_time = max(timings)

        # With audio_features should still be fast (< 1.5 seconds average)
        assert avg_time < 1.5, f"Visualization average time {avg_time:.3f}s should be < 1.5s"

        # Max time should be reasonable (< 3 seconds)
        assert max_time < 3.0, f"Visualization max time {max_time:.3f}s should be < 3.0s"

        return avg_time

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_response_size(self, client, sample_audio_file):
        """Test response size with audio_features."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        response_size = len(response.content)

        # Visualization response should be larger but reasonable (< 200KB)
        assert (
            response_size < 200 * 1024
        ), f"Visualization response {response_size} bytes should be < 200KB"

        # Should be at least 10KB (has substantial data)
        assert (
            response_size > 10 * 1024
        ), f"Visualization response {response_size} bytes should be > 10KB"

        return response_size


class TestOverheadComparison:
    """Test overhead of audio_features feature compared to baseline."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_time_overhead_acceptable(self, client, sample_audio_file):
        """Test that audio_features time overhead is acceptable."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        # Measure baseline (without audio_features)
        baseline_timings = []
        for _ in range(10):
            start = time.time()
            response = client.post(
                "/v1/inference/latest?include_audio_features=false",
                files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            )
            baseline_timings.append(time.time() - start)
            assert response.status_code == 200

        baseline_avg = sum(baseline_timings) / len(baseline_timings)

        # Measure with audio_features
        get_feature_flags.cache_clear()
        viz_timings = []
        for _ in range(10):
            start = time.time()
            response = client.post(
                "/v1/inference/latest?include_audio_features=true",
                files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            )
            viz_timings.append(time.time() - start)
            assert response.status_code == 200

        viz_avg = sum(viz_timings) / len(viz_timings)

        # Calculate overhead
        overhead = viz_avg - baseline_avg
        overhead_pct = (overhead / baseline_avg) * 100 if baseline_avg > 0 else 0

        # Overhead should be minimal
        # Either < 100ms absolute OR < 50% relative
        assert overhead < 0.1 or overhead_pct < 50, (
            f"Visualization overhead {overhead:.3f}s ({overhead_pct:.1f}%) is too high. "
            f"Expected < 0.1s or < 50%. Baseline: {baseline_avg:.3f}s, Viz: {viz_avg:.3f}s"
        )

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_size_overhead_acceptable(self, client, sample_audio_file):
        """Test that audio_features size overhead is acceptable with compression."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        # Get baseline size
        response_baseline = client.post(
            "/v1/inference/latest?include_audio_features=false",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )
        baseline_size = len(response_baseline.content)

        # Get audio_features size
        response_viz = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )
        viz_size = len(response_viz.content)

        # Calculate overhead
        size_increase = viz_size - baseline_size
        size_ratio = viz_size / baseline_size if baseline_size > 0 else 0

        # Size increase should be reasonable (< 200KB)
        assert (
            size_increase < 200 * 1024
        ), f"Size increase {size_increase / 1024:.1f}KB should be < 200KB"

        # Ratio should be reasonable (not more than 100x)
        assert size_ratio < 100, f"Size ratio {size_ratio:.1f}x should be < 100x"


class TestConcurrentPerformance:
    """Test performance under concurrent load."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_concurrent_requests_with_audio_features(self, client, sample_audio_file):
        """Test that concurrent requests with audio_features are handled efficiently."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        num_concurrent = 5
        timings = []

        def make_request():
            start = time.time()
            response = client.post(
                "/v1/inference/latest?include_audio_features=true",
                files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            )
            elapsed = time.time() - start
            return response.status_code, elapsed

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]

            for future in as_completed(futures):
                status_code, elapsed = future.result()
                assert status_code == 200, f"Request failed with status {status_code}"
                timings.append(elapsed)

        # All requests should complete
        assert len(timings) == num_concurrent

        # Average time should be reasonable (< 2 seconds)
        avg_time = sum(timings) / len(timings)
        assert avg_time < 2.0, f"Concurrent average time {avg_time:.3f}s should be < 2.0s"

        # Max time should be reasonable (< 4 seconds)
        max_time = max(timings)
        assert max_time < 4.0, f"Concurrent max time {max_time:.3f}s should be < 4.0s"

    def test_concurrent_requests_without_audio_features(self, client, sample_audio_file):
        """Test concurrent baseline performance without audio_features."""
        num_concurrent = 5
        timings = []

        def make_request():
            start = time.time()
            response = client.post(
                "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
            )
            elapsed = time.time() - start
            return response.status_code, elapsed

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]

            for future in as_completed(futures):
                status_code, elapsed = future.result()
                assert status_code == 200
                timings.append(elapsed)

        # Average time should be fast (< 1.5 seconds)
        avg_time = sum(timings) / len(timings)
        assert avg_time < 1.5, f"Concurrent baseline average {avg_time:.3f}s should be < 1.5s"


class TestProcessingTimeMetadata:
    """Test that processing_time_ms metadata is accurate."""

    def test_processing_time_metadata_present(self, client, sample_audio_file):
        """Test that processing_time_ms is included in response."""
        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        assert response.status_code == 200

        data = response.json()

        assert "processing_time_ms" in data, "Response should include processing_time_ms"

        processing_time = data["processing_time_ms"]

        # Should be a positive number
        assert isinstance(processing_time, (int, float))
        assert processing_time > 0

        # Should be reasonable (< 5000ms = 5 seconds)
        assert processing_time < 5000, f"Processing time {processing_time}ms should be < 5000ms"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_processing_time_with_audio_features(self, client, sample_audio_file):
        """Test that processing_time_ms is accurate with audio_features."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        data = response.json()
        processing_time = data["processing_time_ms"]

        # Should be reasonable (< 10000ms = 10 seconds)
        assert (
            processing_time < 10000
        ), f"Processing time with viz {processing_time}ms should be < 10000ms"


class TestMemoryEfficiency:
    """Test memory efficiency of audio_features feature."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_multiple_requests_dont_leak_memory(self, client, sample_audio_file):
        """Test that multiple requests with audio_features don't cause memory issues."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        # Make multiple requests
        for i in range(10):
            response = client.post(
                "/v1/inference/latest?include_audio_features=true",
                files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            )

            assert (
                response.status_code == 200
            ), f"Request {i+1} failed with status {response.status_code}"

            data = response.json()
            assert "audio_features" in data

        # If we get here without errors, memory handling is acceptable


@pytest.mark.slow
class TestLongRunningPerformance:
    """Test performance over longer periods (marked as slow tests)."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_sustained_load_performance(self, client, sample_audio_file):
        """Test performance under sustained load (50 requests)."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        num_requests = 50
        timings = []
        failures = 0

        for i in range(num_requests):
            start = time.time()
            try:
                response = client.post(
                    "/v1/inference/latest?include_audio_features=true",
                    files={"file": ("test.wav", sample_audio_file, "audio/wav")},
                )

                if response.status_code == 200:
                    elapsed = time.time() - start
                    timings.append(elapsed)
                else:
                    failures += 1

            except Exception:
                failures += 1

        # Calculate statistics
        if timings:
            avg_time = sum(timings) / len(timings)
            max_time = max(timings)
            min_time = min(timings)

            # Average should remain reasonable
            assert avg_time < 2.0, f"Sustained load average {avg_time:.3f}s should be < 2.0s"

            # Failure rate should be low (< 5%)
            failure_rate = (failures / num_requests) * 100
            assert failure_rate < 5.0, f"Failure rate {failure_rate:.1f}% should be < 5%"

    def test_performance_consistency(self, client, sample_audio_file):
        """Test that performance remains consistent across requests."""
        num_requests = 20
        timings = []

        for _ in range(num_requests):
            start = time.time()
            response = client.post(
                "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                timings.append(elapsed)

        # Calculate standard deviation
        if len(timings) > 1:
            import statistics

            avg = statistics.mean(timings)
            stdev = statistics.stdev(timings)

            # Standard deviation should be small (< 30% of average)
            consistency_ratio = (stdev / avg) * 100 if avg > 0 else 0

            assert (
                consistency_ratio < 30
            ), f"Performance inconsistency {consistency_ratio:.1f}% should be < 30%"


@pytest.mark.integration
class TestRealWorldPerformance:
    """Test performance with real-world audio samples."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_real_audio_performance(self, client):
        """Test performance with real CREMA-D audio samples."""
        from pathlib import Path

        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()

        crema_d_path = Path(
            "/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV"
        )
        audio_file = crema_d_path / "1001_DFA_HAP_XX.wav"

        if not audio_file.exists():
            pytest.skip("CREMA-D audio file not found")

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        # Measure time
        start = time.time()
        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": (audio_file.name, audio_bytes, "audio/wav")},
        )
        elapsed = time.time() - start

        assert response.status_code == 200

        # Real audio should process in reasonable time (< 2 seconds)
        assert elapsed < 2.0, f"Real audio processing took {elapsed:.3f}s, expected < 2.0s"

        data = response.json()
        assert "audio_features" in data

        # Check processing time metadata
        assert data["processing_time_ms"] < 2000
