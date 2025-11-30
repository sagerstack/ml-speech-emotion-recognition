# Local Model Versioning System

This directory contains versioned ML models for speech emotion recognition with automatic discovery and deployment.

## Directory Structure

```
models/
├── v1/
│   ├── model.pkl                # Trained scikit-learn model
│   ├── feature_extractor.py     # Feature extraction logic
│   ├── metadata.json            # Model metadata
│   └── __init__.py              # Python package marker
├── v2/
│   ├── model.pkl
│   ├── feature_extractor.py
│   ├── metadata.json
│   └── __init__.py
└── v3/  (when you add new models...)
    ├── model.pkl
    ├── feature_extractor.py
    ├── metadata.json
    └── __init__.py
```

## Adding a New Model Version

### Step 1: Create Version Directory

```bash
mkdir models/v3
touch models/v3/__init__.py
```

### Step 2: Add Your Trained Model

Copy your trained scikit-learn model (as a pickle file):

```bash
cp /path/to/your/trained_model.pkl models/v3/model.pkl
```

### Step 3: Implement Feature Extractor

Create `models/v3/feature_extractor.py` with this exact interface:

```python
import io
import numpy as np
import librosa

def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
    """
    Extract features from audio bytes.

    CRITICAL: Use the EXACT SAME feature extraction code from training!

    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, M4A, etc.)
        filename: Original filename (e.g., "speech.wav")

    Returns:
        np.ndarray: 1D feature vector of shape (n_features,)
                   Must match what your model expects!
    """
    # Load audio from bytes
    audio_data, sr = librosa.load(
        io.BytesIO(audio_bytes),
        sr=22050,  # Use same sample rate as training
        mono=True
    )

    # Extract features (COPY FROM YOUR TRAINING CODE!)
    features = []

    # Example: MFCCs
    mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13)
    features.append(np.mean(mfccs, axis=1))
    features.append(np.std(mfccs, axis=1))

    # ... add all your other features ...

    # Combine into single array
    feature_vector = np.concatenate(features)

    return feature_vector
```

**Important Notes:**
- The function MUST be named `extract_features`
- It MUST accept `(audio_bytes: bytes, filename: str)` parameters
- It MUST return a 1D `np.ndarray`
- The returned array shape MUST match your model's expected features
- Use the EXACT SAME feature extraction as during training!

### Step 4: Create Metadata File

Create `models/v3/metadata.json`:

```json
{
  "version": "3",
  "model_name": "Your Model Name",
  "model_type": "RandomForestClassifier",
  "description": "Brief description of your model",
  "feature_dimension": 128,
  "feature_extraction": "MFCCs, chroma, spectral features",
  "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
  "num_classes": 6,
  "sklearn_version": "1.6.1",
  "created_date": "2024-01-25",
  "dataset": "CREMA-D",
  "notes": "Any additional notes about the model"
}
```

**Required Fields:**
- `version`: Version number as string (e.g., "3")
- `model_type`: Type of scikit-learn model
- `feature_dimension`: Number of features (critical!)
- `classes`: List of emotion labels
- `num_classes`: Number of classes

### Step 5: Restart Backend

The model will be automatically discovered on startup:

```bash
cd backend
poetry run uvicorn app.main:app --reload
```

You should see:
```
✓ Registered model version 1
✓ Registered model version 2
✓ Registered model version 3
Latest model version: 3
```

## Finding Your Feature Extraction Code

### Option 1: From Training Notebook

1. Open your Jupyter notebook where you trained the model
2. Find the cell that extracts features from audio
3. Copy that exact code into `extract_features()` function

Example notebook cell:
```python
# In your training notebook:
def extract_audio_features(file_path):
    data, sr = librosa.load(file_path, sr=22050)

    mfccs = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfccs, axis=1)
    mfcc_std = np.std(mfccs, axis=1)

    return np.concatenate([mfcc_mean, mfcc_std])
```

Convert to `feature_extractor.py`:
```python
def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
    # Load from bytes instead of file path
    audio_data, sr = librosa.load(io.BytesIO(audio_bytes), sr=22050)

    # Same extraction logic
    mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfccs, axis=1)
    mfcc_std = np.std(mfccs, axis=1)

    return np.concatenate([mfcc_mean, mfcc_std])
```

### Option 2: From Training Script

If you have a Python script:
```bash
# Find feature extraction function
grep -A 50 "def extract" your_training_script.py
```

## Testing Your Feature Extractor

Before deploying, test that it works:

```python
# Test script
import pickle
from models.v3.feature_extractor import extract_features

# Load test audio
with open("test_audio.wav", "rb") as f:
    audio_bytes = f.read()

# Extract features
features = extract_features(audio_bytes, "test_audio.wav")

print(f"Feature shape: {features.shape}")
print(f"Expected shape: ({your_expected_feature_count},)")

# Load model and test prediction
with open("models/v3/model.pkl", "rb") as f:
    model = pickle.load(f)

prediction = model.predict(features.reshape(1, -1))
print(f"Prediction: {prediction}")
```

## API Endpoints (Automatically Available)

Once registered, your model is accessible via:

```bash
# Use latest model (will use v3 if it's the highest version)
POST /api/v1/infer/local/latest

# Use specific version
POST /api/v1/infer/local/3

# Compare across all versions (including v3)
POST /api/v1/infer/local/all

# Get model info
GET /api/v1/models/local/3/info
GET /api/v1/models/local/list
```

## Troubleshooting

### Error: "Feature extractor doesn't implement required interface"

Make sure your `feature_extractor.py` has:
- Function named exactly `extract_features`
- Parameters: `(audio_bytes: bytes, filename: str)`
- Returns: `np.ndarray`

### Error: "Invalid features: expected shape (X,), got (Y,)"

Your feature extractor is returning the wrong number of features. Check:
1. Does your `metadata.json` have correct `feature_dimension`?
2. Does your feature extraction match training?
3. Count the features you're concatenating

### Error: "Model version X not found"

The model wasn't discovered. Check:
1. Directory name must be exactly `v{number}` (e.g., `v3`, not `version3`)
2. All required files exist: `model.pkl`, `feature_extractor.py`, `metadata.json`
3. Restart the backend server

### Warning: "Trying to unpickle estimator from version X.X.X"

Your model was trained with a different scikit-learn version. This may cause issues:
1. Check `sklearn_version` in your `metadata.json`
2. Consider retraining with current sklearn version
3. Or use a virtual environment with matching sklearn version

## Best Practices

1. **Always test locally first** - Verify predictions match training results
2. **Version control** - Keep training notebooks alongside model versions
3. **Document features** - Describe what features you're extracting in metadata
4. **Consistent preprocessing** - Use same sample rates, normalization, etc.
5. **Validate shape** - Always check feature vector shape matches model expectations

## Current Models

### v1: Decision Tree Classifier
- **Features**: 162 dimensions
- **Type**: DecisionTreeClassifier
- **Status**: ⚠️ Feature extractor needs implementation

### v2: SVM with MFCC Features
- **Features**: 78 dimensions
- **Type**: Pipeline (StandardScaler + RFE + SVC)
- **Status**: ⚠️ Feature extractor needs implementation

## Need Help?

1. Check the interface contract in `app/interfaces/feature_extractor.py`
2. Look at examples in existing `feature_extractor.py` files
3. Review your training notebook for feature extraction code
4. Ensure all dependencies (librosa, numpy) are installed

## Next Steps

After implementing feature extractors:
1. Test with sample audio files
2. Verify predictions match training results
3. Deploy to production
4. Monitor inference performance via `/metrics` endpoint
