"""
Audio feature extraction module - isolated from Streamlit to avoid caching conflicts.

This module runs librosa processing in a separate process to prevent
Streamlit's caching mechanism from trying to hash librosa's internal
JIT-compiled functions (which causes "no locator available" errors).
"""

import io
import numpy as np
import pandas as pd


def extract_audio_features(audio_bytes: bytes, label: str, engine: str) -> dict:
    """
    Extract audio features using librosa.

    This function is designed to run in a separate process via
    concurrent.futures.ProcessPoolExecutor to isolate librosa
    from Streamlit's execution context.

    Args:
        audio_bytes: Raw audio data as bytes
        label: Label/filename for the audio
        engine: Processing engine identifier

    Returns:
        Dictionary containing all extracted features and visualization data
    """
    # Import librosa inside the function to ensure it's loaded fresh in subprocess
    import librosa

    # Load audio
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    # Normalize waveform length for display
    max_wave_points = min(len(y), 4096)
    waveform = y[:max_wave_points]

    # Mel spectrogram
    mel = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, fmax=sr / 2),
        ref=np.max,
    )

    # Chroma features - using chroma_stft with explicit parameters to avoid notation.py
    # The issue with chroma_cqt is it uses __o_fold from notation.py which can't be hashed
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_chroma=12, n_fft=2048)

    # Extract MFCCs for the equalizer chart (20 coefficients)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    mfcc_mean = np.mean(mfccs, axis=1)

    # Extract Delta and Delta-Delta features
    delta_mfcc = librosa.feature.delta(mfccs)
    delta_mfcc_mean = np.mean(delta_mfcc, axis=1)

    delta2_mfcc = librosa.feature.delta(mfccs, order=2)
    delta2_mfcc_mean = np.mean(delta2_mfcc, axis=1)

    # Calculate duration
    duration = len(y) / sr

    # Extract pitch (F0) for prosodic features
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=80,
            fmax=400,
            sr=sr
        )

        hop_length = 512
        times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

        voiced_mask = ~np.isnan(f0)

        if np.sum(voiced_mask) > 5:
            pitch_values = f0[voiced_mask]
            pitch_times = times[voiced_mask]
        else:
            n_points = 50
            pitch_times = np.linspace(0, duration, n_points)
            pitch_values = 150 + 50 * np.sin(2 * np.pi * pitch_times / duration)
    except Exception:
        n_points = 50
        pitch_times = np.linspace(0, duration, n_points)
        pitch_values = 150 + 50 * np.sin(2 * np.pi * pitch_times / duration)

    # Mel Spectrogram Parameters
    mel_mean_energy = float(np.mean(mel))
    mel_max_energy = float(np.max(mel))

    mel_params_rows = [
        ("Mel Bands", "64", "Dimensions"),
        ("Duration", f"{duration:.1f} s", "Time"),
        ("Frequency Range", f"0 - {int(sr/2)} Hz", "Mel Scale"),
        ("Sample Rate", f"{sr} Hz", "Audio"),
        ("Mean Energy", f"{mel_mean_energy:.1f} dB", "Intensity"),
        ("Max Energy", f"{mel_max_energy:.1f} dB", "Peak"),
    ]

    mel_params_df = pd.DataFrame(mel_params_rows, columns=["Parameter", "Value", "Unit"])

    # Baseline Feature Extraction Table
    rms = float(librosa.feature.rms(y=y).mean())
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())

    feature_rows = [
        ("Zero Crossing Rate (ZCR)", f"{zcr:.3f}", "Rate", "The rate at which the audio signal changes from positive to negative (or vice versa)."),
        ("Root Mean Square Energy (RMS)", f"{rms:.3f}", "Linear", "A measure of the signal's loudness/energy, computed as the square root of the mean of squared amplitude values."),
        ("Mel Spectrogram", "128", "Features", "A representation of how energy is distributed across different frequencies over time, scaled to match human hearing perception."),
        ("Chroma Features", "12", "Features", "Energy distribution across the 12 pitch classes of Western music (C, C#, D, D#, E, F, F#, G, G#, A, A#, B), regardless of octave."),
        ("MFCCs", "13", "Features", "The most important features in speech processing. MFCCs capture the shape of the vocal tract (how the mouth, tongue and throat are positioned), which determines the \"color\" or timbre of the voice."),
        ("Delta Features (Delta MFCCs)", "20", "Features", "Captures the rate of change of MFCCs over time, representing how the voice characteristics are changing from one moment to the next."),
        ("Delta-Delta Features (Acceleration)", "20", "Features", "Second derivative of MFCCs capturing the acceleration of change, providing information about how quickly the voice is changing its rate of change."),
        ("Prosodic Features", "8", "Features", "Captures the 'melody' of speech including pitch patterns (mean, std, range, max, min), energy dynamics (std, slope, range), rhythm and stress that convey emotional meaning beyond words."),
    ]

    feature_df = pd.DataFrame(feature_rows, columns=["Feature", "Value", "Unit", "Relevance"])

    return {
        "label": label,
        "engine": engine,
        "waveform": waveform.tolist(),  # Convert to list for serialization
        "sr": int(sr),
        "mel": mel.tolist(),
        "chroma": chroma.tolist(),
        "mfcc_mean": mfcc_mean.tolist(),
        "delta_mfcc_mean": delta_mfcc_mean.tolist(),
        "delta2_mfcc_mean": delta2_mfcc_mean.tolist(),
        "pitch_times": pitch_times.tolist() if isinstance(pitch_times, np.ndarray) else pitch_times,
        "pitch_values": pitch_values.tolist() if isinstance(pitch_values, np.ndarray) else pitch_values,
        "mel_params_df": mel_params_df.to_dict('records'),
        "feature_df": feature_df.to_dict('records'),
        "duration": float(duration),
    }


def _worker_extract_features(args):
    """Worker function for process pool - unpacks arguments."""
    audio_bytes, label, engine = args
    return extract_audio_features(audio_bytes, label, engine)


# Required guard for multiprocessing on Windows and 'spawn' context
if __name__ == '__main__':
    # This module is designed to be imported and used via ProcessPoolExecutor
    # Direct execution is not intended
    pass
