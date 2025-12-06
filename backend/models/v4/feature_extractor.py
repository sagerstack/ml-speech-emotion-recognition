"""
Feature Extractor for Model v4 (Ultra Ensemble Model)

This extractor uses the EXACT SAME feature extraction logic from training.
Produces 210 features: Original (162) + Delta MFCCs (20) + Delta-Delta MFCCs (20) + Prosodic (8)

Training parameters:
- Duration: 2.5 seconds
- Offset: 0.6 seconds
- Sample rate: default (22050 Hz)
- n_mfcc: 20
- Audio trimming: top_db=20 (removes leading/trailing silence)
"""

import io
from typing import Dict
import numpy as np
import librosa


def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
    """
    Extract 210 enhanced features from audio bytes for v4 model.

    This matches the exact feature extraction used during training:

    Original Features (162):
    - Zero Crossing Rate (1 feature)
    - Chroma STFT (12 features)
    - MFCC (20 features)
    - RMS (1 feature)
    - Mel Spectrogram (128 features)

    Delta Features (40):
    - Delta MFCC (20 features) - first derivative
    - Delta-Delta MFCC (20 features) - second derivative

    Prosodic Features (8):
    - Pitch statistics: mean, std, range, max, min (5 features)
    - Energy dynamics: std, slope, range (3 features)

    Total: 210 features

    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename (used for format detection)

    Returns:
        np.ndarray: Feature vector of shape (210,)

    Raises:
        ValueError: If audio cannot be loaded or processed
    """
    try:
        # Load audio from bytes with same parameters as training
        # duration=2.5, offset=0.6 to skip silence at start/end
        data, sr = librosa.load(
            io.BytesIO(audio_bytes),
            duration=2.5,
            offset=0.6
        )

        # CRITICAL: Trim leading/trailing silence (matches training)
        data, _ = librosa.effects.trim(data, top_db=20)

        # Initialize result array
        result = np.array([])

        # === ORIGINAL FEATURES (162) ===

        # 1. Zero Crossing Rate (1 feature)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y=data).T, axis=0)
        result = np.hstack((result, zcr))

        # 2. Chroma STFT (12 features)
        stft = np.abs(librosa.stft(data))
        chroma_stft = np.mean(librosa.feature.chroma_stft(S=stft, sr=sr).T, axis=0)
        result = np.hstack((result, chroma_stft))

        # 3. MFCC (20 features)
        mfcc = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=20)
        mfcc_mean = np.mean(mfcc.T, axis=0)
        result = np.hstack((result, mfcc_mean))

        # 4. Root Mean Square Value (1 feature)
        rms = np.mean(librosa.feature.rms(y=data).T, axis=0)
        result = np.hstack((result, rms))

        # 5. Mel Spectrogram (128 features)
        mel = np.mean(librosa.feature.melspectrogram(y=data, sr=sr).T, axis=0)
        result = np.hstack((result, mel))

        # === DELTA FEATURES (40) ===

        # 6. Delta MFCC (20 features) - first derivative
        delta_mfcc = librosa.feature.delta(mfcc)
        delta_mfcc_mean = np.mean(delta_mfcc.T, axis=0)
        result = np.hstack((result, delta_mfcc_mean))

        # 7. Delta-Delta MFCC (20 features) - second derivative
        delta2_mfcc = librosa.feature.delta(mfcc, order=2)
        delta2_mfcc_mean = np.mean(delta2_mfcc.T, axis=0)
        result = np.hstack((result, delta2_mfcc_mean))

        # === PROSODIC FEATURES (8) ===

        # 8. Pitch statistics (5 features)
        pitches, magnitudes = librosa.piptrack(y=data, sr=sr)
        pitch_values = pitches[pitches > 0]

        if len(pitch_values) > 0:
            pitch_mean = np.mean(pitch_values)
            pitch_std = np.std(pitch_values)
            pitch_max = np.max(pitch_values)
            pitch_min = np.min(pitch_values)
            pitch_range = pitch_max - pitch_min
        else:
            pitch_mean = pitch_std = pitch_max = pitch_min = pitch_range = 0

        # 9. Energy dynamics (3 features)
        rms_full = librosa.feature.rms(y=data)[0]
        energy_std = np.std(rms_full)
        energy_slope = np.polyfit(range(len(rms_full)), rms_full, 1)[0] if len(rms_full) > 1 else 0
        energy_range = np.max(rms_full) - np.min(rms_full) if len(rms_full) > 0 else 0

        # Combine prosodic features
        prosodic = np.array([
            pitch_mean, pitch_std, pitch_range, pitch_max, pitch_min,
            energy_std, energy_slope, energy_range
        ])
        result = np.hstack((result, prosodic))

        # Verify shape
        if result.shape[0] != 210:
            raise ValueError(f"Expected 210 features, got {result.shape[0]}")

        return result

    except Exception as e:
        raise ValueError(f"Failed to extract features from audio: {str(e)}")


def extract_features_with_audio_data(audio_bytes: bytes, filename: str) -> Dict:
    """
    Extract 210 enhanced features AND intermediate audio_features matrices from audio bytes.

    This function extracts the same 210 features as extract_features() but additionally
    captures intermediate matrices BEFORE averaging for frontend audio_features:
    - Waveform (trimmed audio data)
    - Mel spectrogram (128 × T)
    - Chroma STFT (12 × T)
    - MFCCs (20 × T)
    - Delta MFCCs (20 × T)
    - Delta-Delta MFCCs (20 × T)
    - Pitch contour with times
    - RMS energy contour

    The existing extract_features() function remains unchanged for backward compatibility.

    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename (used for format detection)

    Returns:
        Dict with two keys:
            "features": np.ndarray of shape (210,) - for model inference
            "audio_features": Dict containing:
                - "waveform": List[float] - trimmed audio samples
                - "sample_rate": int - audio sample rate (Hz)
                - "duration": float - audio duration (seconds)
                - "mel_spectrogram": List[List[float]] - shape (128, T)
                - "chroma": List[List[float]] - shape (12, T)
                - "mfcc": List[List[float]] - shape (20, T)
                - "delta_mfcc": List[List[float]] - shape (20, T)
                - "delta_delta_mfcc": List[List[float]] - shape (20, T)
                - "pitch_times": List[float] - time points for pitch
                - "pitch_values": List[float] - pitch frequency (Hz)
                - "rms_contour": List[float] - RMS energy over time

    Raises:
        ValueError: If audio cannot be loaded or processed

    Example:
        >>> result = extract_features_with_audio_data(audio_bytes, "speech.wav")
        >>> features = result["features"]  # (210,) for model
        >>> viz_data = result["audio_features"]
        >>> mel_spec = viz_data["mel_spectrogram"]  # (128, T) matrix
    """
    try:
        # Load audio from bytes with same parameters as training
        # duration=2.5, offset=0.6 to skip silence at start/end
        data, sr = librosa.load(
            io.BytesIO(audio_bytes),
            duration=2.5,
            offset=0.6
        )

        # CRITICAL: Trim leading/trailing silence (matches training)
        data, _ = librosa.effects.trim(data, top_db=20)

        # Capture audio metadata
        duration = len(data) / sr

        # Initialize result array for features
        result = np.array([])

        # === ORIGINAL FEATURES (162) ===

        # 1. Zero Crossing Rate (1 feature)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y=data).T, axis=0)
        result = np.hstack((result, zcr))

        # 2. Chroma STFT (12 features) - CAPTURE BEFORE AVERAGING
        stft = np.abs(librosa.stft(data))
        chroma_stft = librosa.feature.chroma_stft(S=stft, sr=sr)  # (12, T)
        chroma_stft_mean = np.mean(chroma_stft.T, axis=0)
        result = np.hstack((result, chroma_stft_mean))

        # 3. MFCC (20 features) - CAPTURE BEFORE AVERAGING
        mfcc = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=20)  # (20, T)
        mfcc_mean = np.mean(mfcc.T, axis=0)
        result = np.hstack((result, mfcc_mean))

        # 4. Root Mean Square Value (1 feature) - CAPTURE FULL CONTOUR
        rms_full = librosa.feature.rms(y=data)[0]  # (T,)
        rms = np.mean(rms_full)
        result = np.hstack((result, rms))

        # 5. Mel Spectrogram (128 features) - CAPTURE BEFORE AVERAGING
        mel = librosa.feature.melspectrogram(y=data, sr=sr)  # (128, T)
        mel_mean = np.mean(mel.T, axis=0)
        result = np.hstack((result, mel_mean))

        # === DELTA FEATURES (40) ===

        # 6. Delta MFCC (20 features) - first derivative - CAPTURE BEFORE AVERAGING
        delta_mfcc = librosa.feature.delta(mfcc)  # (20, T)
        delta_mfcc_mean = np.mean(delta_mfcc.T, axis=0)
        result = np.hstack((result, delta_mfcc_mean))

        # 7. Delta-Delta MFCC (20 features) - second derivative - CAPTURE BEFORE AVERAGING
        delta2_mfcc = librosa.feature.delta(mfcc, order=2)  # (20, T)
        delta2_mfcc_mean = np.mean(delta2_mfcc.T, axis=0)
        result = np.hstack((result, delta2_mfcc_mean))

        # === PROSODIC FEATURES (8) ===

        # 8. Pitch statistics (5 features) - CAPTURE PITCH CONTOUR
        pitches, magnitudes = librosa.piptrack(y=data, sr=sr)  # (freq_bins, T)

        # Extract pitch contour (max pitch per time frame)
        pitch_contour = []
        pitch_times = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_contour.append(float(pitch))
                pitch_times.append(float(t * 512 / sr))  # Convert frame to time

        # Calculate pitch statistics for features
        pitch_values = pitches[pitches > 0]
        if len(pitch_values) > 0:
            pitch_mean = np.mean(pitch_values)
            pitch_std = np.std(pitch_values)
            pitch_max = np.max(pitch_values)
            pitch_min = np.min(pitch_values)
            pitch_range = pitch_max - pitch_min
        else:
            pitch_mean = pitch_std = pitch_max = pitch_min = pitch_range = 0

        # 9. Energy dynamics (3 features)
        energy_std = np.std(rms_full)
        energy_slope = np.polyfit(range(len(rms_full)), rms_full, 1)[0] if len(rms_full) > 1 else 0
        energy_range = np.max(rms_full) - np.min(rms_full) if len(rms_full) > 0 else 0

        # Combine prosodic features
        prosodic = np.array([
            pitch_mean, pitch_std, pitch_range, pitch_max, pitch_min,
            energy_std, energy_slope, energy_range
        ])
        result = np.hstack((result, prosodic))

        # Verify shape
        if result.shape[0] != 210:
            raise ValueError(f"Expected 210 features, got {result.shape[0]}")

        # === PREPARE VISUALIZATION DATA ===
        # Convert all numpy arrays to lists for JSON serialization
        audio_features_data = {
            # Audio metadata
            "sample_rate": int(sr),
            "duration": float(duration),

            # Waveform
            "waveform": data.tolist(),

            # Spectral features (matrices)
            "mel_spectrogram": mel.tolist(),  # (128, T)
            "chroma": chroma_stft.tolist(),  # (12, T)
            "mfcc": mfcc.tolist(),  # (20, T)
            "delta_mfcc": delta_mfcc.tolist(),  # (20, T)
            "delta_delta_mfcc": delta2_mfcc.tolist(),  # (20, T)

            # Prosodic features (time series)
            "pitch_times": pitch_times,  # Time points
            "pitch_values": pitch_contour,  # Pitch frequency at each time
            "rms_contour": rms_full.tolist(),  # (T,)
        }

        return {
            "features": result,  # (210,) numpy array for model
            "audio_features": audio_features_data  # Dict with lists for JSON
        }

    except Exception as e:
        raise ValueError(f"Failed to extract features with audio_features from audio: {str(e)}")
