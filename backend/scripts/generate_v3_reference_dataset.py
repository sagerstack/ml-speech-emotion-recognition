"""
Generate Evidently Reference Dataset for v3 Model Monitoring

This script creates the reference dataset for Evidently monitoring by:
1. Loading CREMA-D audio files
2. Using the same train/test split as model training (test_size=0.25, random_state=42)
3. Extracting features using v3 feature extractor
4. Applying StandardScaler from v3 model bundle
5. Saving to CSV for Evidently monitoring

Output: backend/monitoring_data/v3_reference_dataset.csv
Expected: ~5,581 rows (75% of 7,442 files), 211 columns (210 features + actual_emotion)
"""

import os
import sys
import pickle
from pathlib import Path
from typing import Tuple, List

import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn.model_selection import train_test_split

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.v3.feature_extractor import extract_features


# Define UltraEnsembleModel stub for unpickling
# This allows us to load the model bundle without needing the full model implementation
class UltraEnsembleModel:
    """Stub class for unpickling v3 model bundle"""
    pass


# Configuration
AUDIO_DIR = "/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV/"
MODEL_PATH = Path(__file__).parent.parent / "models" / "v3" / "model.pkl"
OUTPUT_PATH = Path(__file__).parent.parent / "monitoring_data" / "v3_reference_dataset.csv"
TEST_SIZE = 0.25
RANDOM_STATE = 42

# Emotion mapping from CREMA-D filename codes
EMOTION_MAP = {
    'ANG': 'angry',
    'DIS': 'disgust',
    'FEA': 'fear',
    'HAP': 'happy',
    'NEU': 'neutral',
    'SAD': 'sad'
}


def parse_emotion_from_filename(filename: str) -> str:
    """
    Extract emotion label from CREMA-D filename.

    Format: {ActorID}_{SeriesCode}_{EmotionCode}_{LevelCode}.wav
    Example: 1001_DFA_ANG_XX.wav -> "angry"

    Args:
        filename: Audio filename from CREMA-D dataset

    Returns:
        Emotion label (angry, disgust, fear, happy, neutral, sad)
    """
    parts = filename.replace('.wav', '').split('_')
    if len(parts) >= 3:
        emotion_code = parts[2]
        return EMOTION_MAP.get(emotion_code, 'unknown')
    return 'unknown'


def load_scaler():
    """
    Load StandardScaler from v3 model bundle.

    Returns:
        StandardScaler instance from trained model

    Raises:
        FileNotFoundError: If model.pkl doesn't exist
        KeyError: If scaler not found in model bundle
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model bundle not found at {MODEL_PATH}")

    print(f"Loading scaler from {MODEL_PATH}...")
    with open(MODEL_PATH, 'rb') as f:
        bundle = pickle.load(f)

    if 'scaler' not in bundle:
        raise KeyError("Scaler not found in model bundle")

    return bundle['scaler']


def load_audio_files() -> Tuple[List[str], List[str]]:
    """
    Scan AudioWAV directory and parse emotion labels.

    Returns:
        Tuple of (file_paths, emotions)

    Raises:
        FileNotFoundError: If audio directory doesn't exist
    """
    if not os.path.exists(AUDIO_DIR):
        raise FileNotFoundError(f"Audio directory not found: {AUDIO_DIR}")

    print(f"Scanning audio directory: {AUDIO_DIR}")

    file_paths = []
    emotions = []

    for filename in os.listdir(AUDIO_DIR):
        if not filename.lower().endswith('.wav'):
            continue

        emotion = parse_emotion_from_filename(filename)
        if emotion == 'unknown':
            continue

        file_paths.append(os.path.join(AUDIO_DIR, filename))
        emotions.append(emotion)

    print(f"Found {len(file_paths)} valid audio files")
    return file_paths, emotions


def extract_features_for_split(file_paths: List[str], emotions: List[str]) -> Tuple[np.ndarray, List[str], int, int]:
    """
    Extract features for training split only (skipping test split).

    Args:
        file_paths: List of audio file paths
        emotions: List of emotion labels

    Returns:
        Tuple of (features, emotions, success_count, failure_count)
    """
    features_list = []
    emotions_list = []
    success_count = 0
    failure_count = 0

    print(f"\nExtracting features for {len(file_paths)} audio files...")

    for file_path, emotion in tqdm(zip(file_paths, emotions), total=len(file_paths), desc="Processing"):
        try:
            # Load audio file
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()

            # Extract 210 features
            features = extract_features(audio_bytes, os.path.basename(file_path))

            # Verify feature shape
            if features.shape[0] != 210:
                print(f"\nWarning: Expected 210 features, got {features.shape[0]} for {file_path}")
                failure_count += 1
                continue

            features_list.append(features)
            emotions_list.append(emotion)
            success_count += 1

        except Exception as e:
            print(f"\nError processing {file_path}: {str(e)}")
            failure_count += 1
            continue

    # Convert to numpy array
    features_array = np.array(features_list) if features_list else np.array([])

    return features_array, emotions_list, success_count, failure_count


def generate_reference_dataset():
    """
    Main function to generate reference dataset.

    Process:
    1. Scan AudioWAV directory
    2. Parse emotion labels
    3. Train/test split (test_size=0.25, random_state=42)
    4. Extract features for TRAINING split only
    5. Apply scaler from v3 model
    6. Save to CSV
    """
    print("=" * 80)
    print("Generating Evidently Reference Dataset for v3 Model")
    print("=" * 80)

    # Step 1: Load audio files and parse emotions
    file_paths, emotions = load_audio_files()

    if len(file_paths) == 0:
        print("\nError: No valid audio files found!")
        return

    # Print emotion distribution
    print("\nEmotion distribution:")
    emotion_counts = pd.Series(emotions).value_counts()
    for emotion, count in emotion_counts.items():
        print(f"  {emotion:10s}: {count:4d} samples")

    # Step 2: Train/test split (same as model training)
    print(f"\nSplitting data (test_size={TEST_SIZE}, random_state={RANDOM_STATE})...")
    X_train_paths, X_test_paths, y_train, y_test = train_test_split(
        file_paths,
        emotions,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=emotions
    )

    print(f"Training split: {len(X_train_paths)} files")
    print(f"Test split: {len(X_test_paths)} files")

    # Step 3: Extract features for TRAINING split only
    features, emotions_filtered, success_count, failure_count = extract_features_for_split(
        X_train_paths, y_train
    )

    print(f"\n{'='*80}")
    print(f"Feature extraction complete:")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")
    print(f"  Total: {success_count + failure_count}")

    if features.shape[0] == 0:
        print("\nError: No features extracted!")
        return

    print(f"\nExtracted features shape: {features.shape}")

    # Step 4: Load scaler and apply transformation
    try:
        scaler = load_scaler()
        print("\nApplying StandardScaler transformation...")
        features_scaled = scaler.transform(features)
        print(f"Scaled features shape: {features_scaled.shape}")
    except Exception as e:
        print(f"\nError loading/applying scaler: {str(e)}")
        return

    # Step 5: Create DataFrame with proper columns
    print("\nCreating DataFrame...")

    # Feature column names: feature_0, feature_1, ..., feature_209
    feature_columns = [f"feature_{i}" for i in range(210)]

    # Create DataFrame
    df = pd.DataFrame(features_scaled, columns=feature_columns)
    df['actual_emotion'] = emotions_filtered

    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {len(df.columns)} (210 features + 1 label)")

    # Print final emotion distribution
    print("\nFinal emotion distribution in reference dataset:")
    final_counts = df['actual_emotion'].value_counts()
    for emotion, count in final_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {emotion:10s}: {count:4d} samples ({percentage:5.1f}%)")

    # Step 6: Save to CSV
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving reference dataset to: {OUTPUT_PATH}")
    df.to_csv(OUTPUT_PATH, index=False)

    # Verify saved file
    file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved successfully! File size: {file_size_mb:.2f} MB")

    print(f"\n{'='*80}")
    print("Reference dataset generation complete!")
    print(f"{'='*80}")

    # Print summary
    print("\nSummary:")
    print(f"  Total audio files: {len(file_paths)}")
    print(f"  Training split size: {len(X_train_paths)}")
    print(f"  Features extracted: {success_count}")
    print(f"  Failed extractions: {failure_count}")
    print(f"  Final dataset rows: {len(df)}")
    print(f"  Final dataset columns: {len(df.columns)}")
    print(f"  Output file: {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        generate_reference_dataset()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
