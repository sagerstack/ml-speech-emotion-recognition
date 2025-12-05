"""
Test script for inference + feedback system using RAVDESS dataset.

This script:
1. Randomly samples 10 RAVDESS audio files (excluding calm and surprised emotions)
2. Posts inference requests to /v1/infer/local/latest
3. Extracts ground truth emotion from RAVDESS filename
4. Posts feedback with actual emotion to /v1/monitoring/feedback/{prediction_id}
5. Verifies the monitoring report is generated after 10 predictions

Usage:
    poetry run python scripts/test_feedback_system.py
"""

import glob
import os
import random
import time
from pathlib import Path

import requests

# Configuration
API_BASE_URL = "http://localhost:8000/v1"
RAVDESS_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ravdess-speech-audio"
NUM_PREDICTIONS = 10

# RAVDESS emotion code to emotion name mapping (position 3 in filename)
RAVDESS_EMOTION_MAP = {
    "01": "neutral",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fear",  # RAVDESS calls it "fearful", model expects "fear"
    "07": "disgust",
}

# Emotions to skip (not in our 6-class model)
SKIP_EMOTIONS = {"02", "08"}  # calm, surprised


def extract_emotion_from_filename(filename: str) -> str:
    """Extract emotion from RAVDESS filename.

    Format: Modality-VocalChannel-Emotion-Intensity-Statement-Repetition-Actor.wav
    Example: 03-01-06-01-02-01-12.wav -> emotion code is position 3 (06 = fear)
    """
    parts = filename.split("-")
    emotion_code = parts[2]  # Position 3 (0-indexed: position 2)
    return RAVDESS_EMOTION_MAP.get(emotion_code, None)


def find_ravdess_files(num_files: int) -> list[tuple[Path, str]]:
    """Find RAVDESS audio files with compatible emotions and randomly sample them.

    Returns:
        List of tuples: (file_path, actual_emotion)
    """
    all_files = glob.glob(str(RAVDESS_DATA_DIR / "**" / "*.wav"), recursive=True)
    compatible_files = []

    for file_path in all_files:
        filename = os.path.basename(file_path)
        parts = filename.split("-")

        if len(parts) != 7:
            continue

        emotion_code = parts[2]

        # Skip incompatible emotions
        if emotion_code in SKIP_EMOTIONS:
            continue

        actual_emotion = extract_emotion_from_filename(filename)
        if actual_emotion:
            compatible_files.append((Path(file_path), actual_emotion))

    # Randomly sample num_files from all compatible files
    if len(compatible_files) > num_files:
        return random.sample(compatible_files, num_files)

    return compatible_files


def post_inference(file_path: Path) -> tuple[str, str, str]:
    """Post inference request to API.

    Returns:
        Tuple of (prediction_id, predicted_emotion, filename)
    """
    url = f"{API_BASE_URL}/infer/local/latest"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "audio/wav")}
        response = requests.post(url, files=files, timeout=30)

    response.raise_for_status()
    data = response.json()

    prediction_id = data["prediction"]["prediction_id"]
    predicted_emotion = data["prediction"]["emotion"]
    confidence = data["prediction"]["confidence"]

    print(f"✓ Inference: {file_path.name}")
    print(f"  Predicted: {predicted_emotion} (confidence: {confidence:.2f})")
    print(f"  Prediction ID: {prediction_id}")

    return prediction_id, predicted_emotion, file_path.name


def post_feedback(prediction_id: str, actual_emotion: str):
    """Post feedback with actual emotion to monitoring endpoint."""
    url = f"{API_BASE_URL}/monitoring/feedback/{prediction_id}"
    payload = {"actual_emotion": actual_emotion}

    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()

    print(f"✓ Feedback submitted: {actual_emotion}")
    return response.json()


def main():
    """Run the test workflow."""
    print("=" * 80)
    print("Testing Inference + Feedback System with RAVDESS Data")
    print("=" * 80)

    # Find RAVDESS files
    print(f"\n📂 Finding {NUM_PREDICTIONS} RAVDESS audio files...")
    test_files = find_ravdess_files(NUM_PREDICTIONS)

    if len(test_files) < NUM_PREDICTIONS:
        print(f"⚠️  Warning: Only found {len(test_files)} compatible files")

    print(f"✓ Found {len(test_files)} compatible RAVDESS files")

    # Process each file
    results = []
    for i, (file_path, actual_emotion) in enumerate(test_files, 1):
        print(f"\n[{i}/{len(test_files)}] Processing: {file_path.name}")
        print(f"  Ground Truth: {actual_emotion}")

        try:
            # Step 1: Post inference
            prediction_id, predicted_emotion, filename = post_inference(file_path)

            # Step 2: Post feedback
            post_feedback(prediction_id, actual_emotion)

            # Track results
            correct = predicted_emotion == actual_emotion
            results.append(
                {
                    "filename": filename,
                    "predicted": predicted_emotion,
                    "actual": actual_emotion,
                    "correct": correct,
                }
            )

            print(f"  Match: {'✓ CORRECT' if correct else '✗ INCORRECT'}")

            # Small delay between requests
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            continue

    # Print summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    if results:
        correct_count = sum(1 for r in results if r["correct"])
        accuracy = (correct_count / len(results)) * 100

        print(f"\nTotal Predictions: {len(results)}")
        print(f"Correct: {correct_count}")
        print(f"Incorrect: {len(results) - correct_count}")
        print(f"Accuracy: {accuracy:.1f}%")

        print("\nDetailed Results:")
        for i, result in enumerate(results, 1):
            status = "✓" if result["correct"] else "✗"
            print(
                f"  {i}. {status} {result['filename']}: "
                f"predicted={result['predicted']}, actual={result['actual']}"
            )

        print(f"\n📊 Monitoring Report:")
        print(f"  - A report should be auto-generated after 10 predictions")
        print(f"  - Check: backend/monitoring_reports/")
        print(f"  - View dashboard: http://localhost:8080")
        print(f"\n💡 Next Steps:")
        print(f"  1. Check monitoring_reports/ directory for new report")
        print(f"  2. Open Evidently dashboard at http://localhost:8080")
        print(f"  3. Navigate to 'Primary Metrics' tab to see accuracy")
        print(f"  4. Run: poetry run python scripts/configure_rich_dashboard.py")
    else:
        print("\n❌ No successful predictions")

    print("=" * 80)


if __name__ == "__main__":
    main()
