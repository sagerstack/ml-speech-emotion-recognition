#!/usr/bin/env python3
"""
SageMaker Endpoint Testing Script

This script tests the deployed SageMaker endpoint with various audio formats,
concurrent requests, and performance metrics.

Usage Examples:
  poetry run python test_endpoint.py --endpoint speech-emotion-1763477131 --audio path/to/audio.wav
  poetry run python test_endpoint.py --endpoint speech-emotion-1763477131 --emotion happy
  poetry run python test_endpoint.py --endpoint speech-emotion-1763477131 --full
"""

import os
import sys
import json
import time
import logging
import asyncio
import aiohttp
import numpy as np
import librosa
import base64
import concurrent.futures
from typing import Dict, Any, List, Tuple
import boto3
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EndpointTester:
    """Tests SageMaker endpoint functionality and performance."""

    def __init__(self, endpoint_name: str, config_path: str = "config.yaml"):
        """Initialize the endpoint tester."""
        self.endpoint_name = endpoint_name
        self.config_path = config_path
        self.config = self._load_config()
        self.runtime_client = boto3.client('sagemaker-runtime', region_name=self.config['aws']['region'])
        self.session = boto3.Session(region_name=self.config['aws']['region'])

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        try:
            config_file = Path(__file__).parent / self.config_path
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def create_test_audio(self, duration: float = 3.0, sample_rate: int = 16000, emotion: str = "happy") -> np.ndarray:
        """Create synthetic audio with emotional characteristics."""
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # Different frequency patterns for different emotions
        emotion_patterns = {
            "happy": [(300, 0.3), (500, 0.2), (800, 0.15)],  # Higher frequencies
            "sad": [(150, 0.3), (200, 0.2), (300, 0.15)],    # Lower frequencies
            "angry": [(200, 0.4), (400, 0.3), (600, 0.2)],   # Mixed frequencies with energy
            "neutral": [(250, 0.2), (400, 0.15), (600, 0.1)], # Balanced frequencies
            "fearful": [(400, 0.3), (800, 0.25), (1200, 0.2)], # Higher frequencies with variation
            "disgusted": [(100, 0.3), (300, 0.25), (500, 0.2)], # Lower-mid frequencies
        }

        frequencies = emotion_patterns.get(emotion, emotion_patterns["neutral"])
        audio = np.zeros_like(t)

        for freq, amp in frequencies:
            audio += amp * np.sin(2 * np.pi * freq * t)

        # Add modulation for realism
        modulation = 0.1 * np.sin(2 * np.pi * 2 * t)  # 2Hz modulation
        audio = audio * (1 + modulation)

        # Add noise
        noise = np.random.normal(0, 0.05, audio.shape)
        audio = audio + noise

        # Normalize
        audio = np.clip(audio, -1, 1)
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio))

        return audio.astype(np.float32)

    def audio_to_base64(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Convert audio array to base64 string."""
        try:
            # Save to temporary buffer
            import soundfile as sf
            import io

            buffer = io.BytesIO()
            sf.write(buffer, audio, sample_rate, format='WAV')
            buffer.seek(0)

            # Encode to base64
            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            return audio_base64

        except Exception as e:
            logger.error(f"Failed to convert audio to base64: {e}")
            raise

    def load_audio_file(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and return audio array and sample rate."""
        try:
            audio_file_path = Path(audio_path)
            if not audio_file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            logger.info(f"Loading audio file: {audio_file_path}")
            audio, sample_rate = librosa.load(str(audio_file_path), sr=None)

            # Convert to float32 if needed
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Ensure mono channel
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            logger.info(f"✅ Audio loaded: {audio_file_path}")
            logger.info(f"   Sample rate: {sample_rate}Hz")
            logger.info(f"   Duration: {len(audio)/sample_rate:.2f}s")
            logger.info(f"   Shape: {audio.shape}")

            return audio, sample_rate

        except Exception as e:
            logger.error(f"❌ Failed to load audio file {audio_path}: {e}")
            raise

    def test_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """Test endpoint with a specific audio file."""
        try:
            logger.info(f"🎵 Testing endpoint with audio file: {audio_path}")

            # Load audio file
            audio, sample_rate = self.load_audio_file(audio_path)
            audio_base64 = self.audio_to_base64(audio, sample_rate)

            if not audio_base64:
                raise ValueError("Failed to convert audio to base64")

            # Test inference
            start_time = time.time()
            result = self.invoke_endpoint(audio_base64, sample_rate)
            response_time = time.time() - start_time

            # Add metadata
            result.update({
                "audio_file": str(Path(audio_path).name),
                "audio_path": str(Path(audio_path).absolute()),
                "audio_duration": len(audio) / sample_rate,
                "sample_rate": sample_rate,
                "response_time": response_time,
                "audio_shape": audio.shape,
                "test_timestamp": time.time()
            })

            logger.info(f"✅ Audio file test completed (response time: {response_time:.3f}s)")
            return result

        except Exception as e:
            logger.error(f"❌ Audio file test failed: {e}")
            return {
                "audio_file": str(Path(audio_path).name),
                "error": str(e),
                "test_timestamp": time.time(),
                "status": "failed"
            }

    def invoke_endpoint(self, audio_base64: str, sample_rate: int = 16000) -> Dict[str, Any]:
        """Invoke SageMaker endpoint with audio data."""
        try:
            # Prepare input
            input_data = {
                "audio_base64": audio_base64,
                "sample_rate": sample_rate
            }

            payload = json.dumps(input_data)

            # Invoke endpoint
            start_time = time.time()
            response = self.runtime_client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Accept='application/json',
                Body=payload
            )
            end_time = time.time()

            # Parse response
            response_body = response['Body'].read()

            # Debug: Check the type of response_body
            logger.debug(f"Response body type: {type(response_body)}")

            # Handle different response body types
            if isinstance(response_body, str):
                # Response body is already a string
                result = json.loads(response_body)
                response_size = len(response_body.encode('utf-8'))
            elif isinstance(response_body, bytes):
                # Response body is bytes, need to decode
                result = json.loads(response_body.decode('utf-8'))
                response_size = len(response_body)
            else:
                # Unexpected type
                logger.error(f"Unexpected response body type: {type(response_body)}")
                raise ValueError(f"Unexpected response body type: {type(response_body)}")

            # Add timing info
            result['invocation_time'] = end_time - start_time
            result['response_size'] = response_size

            return result

        except Exception as e:
            logger.error(f"Failed to invoke endpoint: {e}")
            return {
                "error": str(e),
                "invocation_time": 0,
                "predicted_emotion": None,
                "confidence": 0
            }

    def test_single_emotion(self, emotion: str, duration: float = 3.0) -> Dict[str, Any]:
        """Test endpoint with a single emotion."""
        try:
            logger.info(f"Testing emotion: {emotion}")

            # Create test audio
            audio = self.create_test_audio(duration=duration, emotion=emotion)
            audio_base64 = self.audio_to_base64(audio)

            # Invoke endpoint
            result = self.invoke_endpoint(audio_base64)

            # Analyze result
            test_result = {
                "test_emotion": emotion,
                "audio_duration": duration,
                "predicted_emotion": result.get("predicted_emotion"),
                "confidence": result.get("confidence", 0),
                "invocation_time": result.get("invocation_time", 0),
                "all_emotions": result.get("all_emotions", {}),
                "success": "error" not in result,
                "correct_prediction": result.get("predicted_emotion") == emotion,
                "error": result.get("error")
            }

            if test_result["success"]:
                logger.info(f"  ✅ {emotion}: {test_result['predicted_emotion']} "
                           f"(confidence: {test_result['confidence']:.3f}, "
                           f"time: {test_result['invocation_time']:.3f}s)")
            else:
                logger.error(f"  ❌ {emotion}: {test_result['error']}")

            return test_result

        except Exception as e:
            logger.error(f"Test failed for emotion {emotion}: {e}")
            return {
                "test_emotion": emotion,
                "error": str(e),
                "success": False
            }

    def test_all_emotions(self) -> List[Dict[str, Any]]:
        """Test endpoint with all supported emotions."""
        try:
            logger.info("🧪 Testing all emotions...")

            emotions = ["happy", "sad", "angry", "neutral", "fearful", "disgusted"]
            results = []

            for emotion in emotions:
                result = self.test_single_emotion(emotion)
                results.append(result)
                time.sleep(0.5)  # Small delay between requests

            # Summary
            successful_tests = [r for r in results if r.get("success", False)]
            correct_predictions = [r for r in successful_tests if r.get("correct_prediction", False)]

            logger.info(f"\n📊 Test Summary:")
            logger.info(f"  Total tests: {len(results)}")
            logger.info(f"  Successful: {len(successful_tests)}")
            logger.info(f"  Correct predictions: {len(correct_predictions)}")
            logger.info(f"  Accuracy: {len(correct_predictions)/len(successful_tests)*100:.1f}%")

            if successful_tests:
                avg_confidence = np.mean([r.get("confidence", 0) for r in successful_tests])
                avg_time = np.mean([r.get("invocation_time", 0) for r in successful_tests])
                logger.info(f"  Average confidence: {avg_confidence:.3f}")
                logger.info(f"  Average response time: {avg_time:.3f}s")

            return results

        except Exception as e:
            logger.error(f"Emotion testing failed: {e}")
            return []

    def test_concurrent_requests(self, num_concurrent: int = 2) -> List[Dict[str, Any]]:
        """Test endpoint with concurrent requests."""
        try:
            logger.info(f"🔄 Testing concurrent requests (n={num_concurrent})")

            def worker_request(worker_id: int) -> Dict[str, Any]:
                """Worker function for concurrent requests."""
                emotion = ["happy", "sad", "angry"][worker_id % 3]
                result = self.test_single_emotion(emotion)
                result["worker_id"] = worker_id
                return result

            # Execute concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                futures = [executor.submit(worker_request, i) for i in range(num_concurrent)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # Analyze results
            successful_requests = [r for r in results if r.get("success", False)]
            total_time = max([r.get("invocation_time", 0) for r in successful_requests]) if successful_requests else 0

            logger.info(f"✅ Concurrent test completed:")
            logger.info(f"  Requests sent: {num_concurrent}")
            logger.info(f"  Successful: {len(successful_requests)}")
            logger.info(f"  Total time: {total_time:.3f}s")

            return results

        except Exception as e:
            logger.error(f"Concurrent testing failed: {e}")
            return []

    def test_audio_formats(self) -> List[Dict[str, Any]]:
        """Test endpoint with different audio formats."""
        try:
            logger.info("🎵 Testing different audio formats...")

            formats = [
                ("short_1s", 1.0),
                ("medium_3s", 3.0),
                ("long_10s", 10.0),
                ("max_30s", 30.0)
            ]

            results = []

            for format_name, duration in formats:
                logger.info(f"Testing {format_name} ({duration}s)...")

                audio = self.create_test_audio(duration=duration)
                audio_base64 = self.audio_to_base64(audio)

                result = self.invoke_endpoint(audio_base64)
                result["test_format"] = format_name
                result["audio_duration"] = duration

                if "error" not in result:
                    logger.info(f"  ✅ {format_name}: {result['predicted_emotion']} "
                               f"(confidence: {result['confidence']:.3f}, "
                               f"time: {result['invocation_time']:.3f}s)")
                else:
                    logger.error(f"  ❌ {format_name}: {result['error']}")

                results.append(result)
                time.sleep(0.5)

            return results

        except Exception as e:
            logger.error(f"Audio format testing failed: {e}")
            return []

    def test_performance_benchmark(self, num_requests: int = 20) -> Dict[str, Any]:
        """Run performance benchmark."""
        try:
            logger.info(f"⚡ Running performance benchmark ({num_requests} requests)...")

            times = []
            confidences = []
            errors = []

            for i in range(num_requests):
                # Vary emotions for realistic testing
                emotion = ["happy", "sad", "angry", "neutral"][i % 4]
                result = self.test_single_emotion(emotion)

                if result.get("success", False):
                    times.append(result.get("invocation_time", 0))
                    confidences.append(result.get("confidence", 0))
                else:
                    errors.append(result.get("error", "Unknown error"))

                # Small delay to avoid throttling
                time.sleep(0.1)

            # Calculate statistics
            benchmark_results = {
                "total_requests": num_requests,
                "successful_requests": len(times),
                "failed_requests": len(errors),
                "success_rate": len(times) / num_requests * 100,
                "response_times": {
                    "min": float(np.min(times)) if times else 0,
                    "max": float(np.max(times)) if times else 0,
                    "mean": float(np.mean(times)) if times else 0,
                    "std": float(np.std(times)) if times else 0,
                    "median": float(np.median(times)) if times else 0,
                    "p95": float(np.percentile(times, 95)) if times else 0,
                    "p99": float(np.percentile(times, 99)) if times else 0
                },
                "confidence_scores": {
                    "min": float(np.min(confidences)) if confidences else 0,
                    "max": float(np.max(confidences)) if confidences else 0,
                    "mean": float(np.mean(confidences)) if confidences else 0,
                    "std": float(np.std(confidences)) if confidences else 0
                },
                "errors": errors[:5]  # First 5 errors
            }

            # Log results
            logger.info(f"\n📊 Performance Benchmark Results:")
            logger.info(f"  Success rate: {benchmark_results['success_rate']:.1f}%")
            logger.info(f"  Response time - Mean: {benchmark_results['response_times']['mean']:.3f}s")
            logger.info(f"  Response time - P95: {benchmark_results['response_times']['p95']:.3f}s")
            logger.info(f"  Response time - P99: {benchmark_results['response_times']['p99']:.3f}s")
            logger.info(f"  Confidence - Mean: {benchmark_results['confidence_scores']['mean']:.3f}")

            # Check if within serverless limits
            max_concurrency = self.config['serverless']['max_concurrency']
            timeout = self.config['serverless']['timeout_in_seconds']

            if benchmark_results['response_times']['max'] > timeout * 0.8:
                logger.warning(f"⚠️  Some requests approach timeout limit ({timeout}s)")

            if benchmark_results['success_rate'] < 95:
                logger.warning(f"⚠️  Low success rate: {benchmark_results['success_rate']:.1f}%")

            return benchmark_results

        except Exception as e:
            logger.error(f"Performance benchmark failed: {e}")
            return {}

    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite."""
        logger.info("🔬 Starting full endpoint test suite...")
        logger.info("=" * 60)

        test_results = {
            "endpoint_name": self.endpoint_name,
            "test_timestamp": time.time(),
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }

        # Test 1: All emotions
        logger.info("\n🧪 Test 1: Emotion Recognition")
        test_results["tests"]["emotion_recognition"] = self.test_all_emotions()

        # Test 2: Audio formats
        logger.info("\n🎵 Test 2: Audio Formats")
        test_results["tests"]["audio_formats"] = self.test_audio_formats()

        # Test 3: Concurrent requests
        logger.info("\n🔄 Test 3: Concurrent Requests")
        max_concurrency = self.config['serverless']['max_concurrency']
        test_results["tests"]["concurrent_requests"] = self.test_concurrent_requests(max_concurrency)

        # Test 4: Performance benchmark
        logger.info("\n⚡ Test 4: Performance Benchmark")
        test_results["tests"]["performance_benchmark"] = self.test_performance_benchmark()

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 Test Suite Summary")

        emotion_tests = test_results["tests"]["emotion_recognition"]
        if emotion_tests:
            successful = [t for t in emotion_tests if t.get("success", False)]
            correct = [t for t in successful if t.get("correct_prediction", False)]
            logger.info(f"  Emotion Recognition: {len(correct)}/{len(successful)} correct "
                       f"({len(correct)/len(successful)*100:.1f}% accuracy)")

        format_tests = test_results["tests"]["audio_formats"]
        if format_tests:
            successful_formats = [t for t in format_tests if "error" not in t]
            logger.info(f"  Audio Formats: {len(successful_formats)}/{len(format_tests)} successful")

        concurrent_tests = test_results["tests"]["concurrent_requests"]
        if concurrent_tests:
            successful_concurrent = [t for t in concurrent_tests if t.get("success", False)]
            logger.info(f"  Concurrent Requests: {len(successful_concurrent)}/{len(concurrent_tests)} successful")

        benchmark = test_results["tests"]["performance_benchmark"]
        if benchmark:
            logger.info(f"  Performance: {benchmark['success_rate']:.1f}% success rate, "
                       f"{benchmark['response_times']['mean']:.3f}s avg response time")

        # Overall assessment
        logger.info("\n🎯 Overall Assessment:")
        all_successful = (
            emotion_tests and len([t for t in emotion_tests if t.get("success", False)]) == len(emotion_tests) and
            format_tests and len([t for t in format_tests if "error" not in t]) == len(format_tests) and
            concurrent_tests and len([t for t in concurrent_tests if t.get("success", False)]) == len(concurrent_tests) and
            benchmark and benchmark.get("success_rate", 0) >= 95
        )

        if all_successful:
            logger.info("  ✅ All tests passed - Endpoint is ready for production!")
        else:
            logger.warning("  ⚠️  Some tests failed - Review results before production use")

        test_results["overall_success"] = all_successful

        return test_results


def main():
    """Main testing function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test SageMaker endpoint")
    parser.add_argument("--endpoint", required=True, help="Name of the SageMaker endpoint to test")
    parser.add_argument("--config", type=str, default="config.yaml", help="Configuration file path")
    parser.add_argument("--audio", type=str, help="Test with specific audio file path")
    parser.add_argument("--emotion", type=str, help="Test specific emotion")
    parser.add_argument("--concurrent", type=int, help="Test concurrent requests")
    parser.add_argument("--benchmark", type=int, help="Run performance benchmark with N requests")
    parser.add_argument("--full", action="store_true", help="Run full test suite")

    args = parser.parse_args()

    try:
        tester = EndpointTester(args.endpoint, args.config)

        if args.audio:
            result = tester.test_audio_file(args.audio)
            print(json.dumps(result, indent=2))

        elif args.emotion:
            result = tester.test_single_emotion(args.emotion)
            print(json.dumps(result, indent=2))

        elif args.concurrent:
            results = tester.test_concurrent_requests(args.concurrent)
            print(json.dumps(results, indent=2))

        elif args.benchmark:
            result = tester.test_performance_benchmark(args.benchmark)
            print(json.dumps(result, indent=2))

        elif args.full:
            results = tester.run_full_test_suite()
            # Save results to file
            output_file = f"test_results_{args.endpoint}_{int(time.time())}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Full test suite completed. Results saved to {output_file}")
            print(json.dumps(results, indent=2))

        else:
            # Default: run emotion tests
            results = tester.test_all_emotions()
            print(json.dumps(results, indent=2))

    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()