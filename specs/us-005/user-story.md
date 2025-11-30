# US-005: Backend-Driven MFCC Feature Visualization for Step 2

## User Story

**As a** data scientist or ML engineer using the emotion recognition system
**I want** to see the actual MFCC features that the model uses for inference
**So that** I can understand what the model is processing and verify feature extraction correctness

## Problem Statement

Currently, Step 2 (Feature Analysis) displays irrelevant audio features that are NOT used by the model:
- ❌ RMS Energy
- ❌ Spectral Centroid
- ❌ Zero Crossing Rate
- ❌ Pitch Mean
- ❌ Standard Spectrogram
- ❌ Chroma Features

The actual model v2 uses **78 MFCC-based features** (MFCCs + Delta + Delta² with mean/std statistics), but these are not visualized.

## Solution Overview

Replace Step 2 visualizations with:
1. **Frequency Band Equalizer** - Visual, intuitive audio spectrum representation
2. **78-Feature Vector Table** - Exact features fed into the ML model

**Architecture:** Backend API extracts ALL features, frontend ONLY visualizes.

## Acceptance Criteria

### Must Have:
- [ ] Backend API endpoint returns both prediction results AND visualization data
- [ ] Step 2 displays equalizer-style frequency spectrum chart
- [ ] Step 2 displays table with all 78 MFCC-based features
- [ ] All irrelevant features (RMS, Spectral Centroid, etc.) are removed
- [ ] Features shown match exactly what `backend/models/v2/feature_extractor.py` extracts
- [ ] Frontend removes local feature extraction (no librosa in Streamlit)
- [ ] Backend handles all audio processing and feature extraction

### Should Have:
- [ ] Equalizer chart is visually appealing with dark theme and cyan accent
- [ ] Feature table is scrollable and well-organized by feature type
- [ ] Processing time metrics are displayed
- [ ] Error handling for API failures

### Nice to Have:
- [ ] Real-time equalizer animation (if feasible)
- [ ] Downloadable feature table (CSV/JSON export)
- [ ] Comparison view showing features from different models

## Design Specifications

### 1. Frequency Band Equalizer Chart

**Visual Design:**
- **Type:** Plotly heatmap
- **X-axis:** Time frames
- **Y-axis:** Frequency bands (8-12 bands: 20Hz-8kHz)
- **Color:** Intensity/energy in dB (dark to cyan gradient)
- **Style:** Dark theme (`plotly_dark`)
- **Accent:** #00d4ff (cyan)
- **Height:** 400px
- **Reference:** Similar to audio spectrum analyzer in professional audio software

**Data Source:** Mel-spectrogram from backend (aggregated into frequency bands)

### 2. 78-Feature Vector Table

**Table Structure:**

| Feature Type | Coefficient | Mean Value | Std Dev |
|--------------|-------------|------------|---------|
| MFCC-1       | 1           | -145.23    | 12.45   |
| MFCC-2       | 2           | 98.76      | 8.92    |
| ...          | ...         | ...        | ...     |
| Delta MFCC-1 | 1           | 2.34       | 1.23    |
| ...          | ...         | ...        | ...     |
| Delta² MFCC-1| 1           | 0.45       | 0.23    |
| ...          | ...         | ...        | ...     |

**Features:**
- Scrollable (height: 400px)
- Grouped by feature type (MFCC, Delta, Delta²)
- Values formatted to 3 decimal places
- Full-width layout

### 3. Step 2 Layout

```
┌──────────────────────────────────────────────────────┐
│  Status message (success with filename)              │
├──────────────────────────────────────────────────────┤
│  🎵 Audio Frequency Spectrum                         │
│  (Equalizer chart - 400px height)                    │
│                                                      │
│  [Frequency Band Equalizer Visualization]           │
├──────────────────────────────────────────────────────┤
│  🔢 Model Input Features (78 MFCC-based features)    │
│  Caption: "These are the exact features extracted    │
│           and fed into the ML model."                │
│                                                      │
│  [78-Feature Vector Table - Scrollable]              │
├──────────────────────────────────────────────────────┤
│  🚀 View Prediction Results Button                   │
└──────────────────────────────────────────────────────┘
```

## Technical Implementation

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Streamlit)                │
│  - Handles user interaction and visualization ONLY      │
│  - No feature extraction or audio processing            │
│  - Displays equalizer + 78-feature table                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ POST /v1/infer/local/2/analyze
                      │ (audio file)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend API (FastAPI)                  │
│  - Receives audio file                                  │
│  - Calls model v2 feature extractor                     │
│  - Returns predictions + visualization data             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ extract_features_with_visualization_data()
                      ▼
┌─────────────────────────────────────────────────────────┐
│          backend/models/v2/feature_extractor.py         │
│  - Extracts 78-feature vector                           │
│  - Extracts mel-spectrogram                             │
│  - Extracts MFCC matrices (13 x time)                   │
│  - Extracts Delta & Delta² MFCC                         │
│  - Returns both inference features + viz data           │
└─────────────────────────────────────────────────────────┘
```

### Backend Changes

#### 1. Enhanced Feature Extractor
**File:** `backend/models/v2/feature_extractor.py`

**New function:** `extract_features_with_visualization_data(audio_bytes: bytes, filename: str)`

**Returns:**
```python
{
    "features_78": np.ndarray,  # (78,) - for model inference
    "visualization_data": {
        "mel_spectrogram": np.ndarray,  # (n_mels, time_frames)
        "mfcc": np.ndarray,  # (13, time_frames)
        "mfcc_delta": np.ndarray,  # (13, time_frames)
        "mfcc_delta2": np.ndarray,  # (13, time_frames)
        "feature_breakdown": [  # For table display
            {"type": "MFCC-1", "coeff": 1, "mean": -145.23, "std": 12.45},
            {"type": "MFCC-2", "coeff": 2, "mean": 98.76, "std": 8.92},
            # ... 78 total entries
        ],
        "sample_rate": 22050,
        "duration": 2.5
    }
}
```

**MFCC Extraction Parameters:**
- Duration: 2.5 seconds
- Offset: 0.6 seconds
- Sample rate: 22050 Hz (default)
- N_MFCC: 13 coefficients
- Features: MFCCs + Delta + Delta² (mean + std for each = 78 total)

#### 2. New API Endpoint
**File:** `backend/app/api/v1/endpoints/inference_local.py`

**New endpoint:** `POST /v1/infer/local/{version}/analyze`

**Request:**
- Multipart form-data with audio file upload

**Response:**
```json
{
  "prediction": {
    "emotion": "happy",
    "confidence": 0.92,
    "all_probabilities": {
      "happy": 0.92,
      "neutral": 0.05,
      "sad": 0.02,
      "angry": 0.01
    }
  },
  "features": {
    "feature_vector_78": [/* 78 float values */],
    "mel_spectrogram": [/* 2D array */],
    "mfcc": [/* 13 x time_frames */],
    "mfcc_delta": [/* 13 x time_frames */],
    "mfcc_delta2": [/* 13 x time_frames */],
    "feature_table": [
      {"type": "MFCC-1", "coeff": 1, "mean": -145.23, "std": 12.45},
      /* ... 78 entries total */
    ],
    "sample_rate": 22050,
    "duration": 2.5
  },
  "metadata": {
    "model_version": "2",
    "processing_time_ms": 145
  }
}
```

#### 3. Model Registry Enhancement
**File:** `backend/app/services/model_registry.py`

**New method:** `extract_features_with_viz(version: str, audio_bytes: bytes, filename: str)`

**Purpose:**
- Call enhanced feature extractor
- Return both 78-feature vector and visualization data
- Keep existing `predict()` method unchanged

### Frontend Changes

#### 1. Remove Local Feature Extraction
**File:** `frontend/streamlit_app/src/ml-app.py`

**REMOVE:** `_generate_local_features()` function (lines 123-166)
- No more librosa usage in frontend
- No local audio processing

**ADD:** `_call_backend_analyze_api(audio_bytes, filename, engine)` function
- Calls backend `/v1/infer/local/2/analyze` endpoint
- Returns features + visualization data

#### 2. Update API Client
**File:** `frontend/streamlit_app/src/real_inference.py` or `api_client.py`

**New method:** `analyze_with_features(audio_bytes, filename, version)`
- POST to `/v1/infer/local/{version}/analyze`
- Return full response with features

#### 3. New Chart Function
**File:** `frontend/streamlit_app/src/feature_charts.py`

**New function:** `frequency_equalizer_chart(mel_spec, sample_rate, accent="#00d4ff")`

**Implementation:**
```python
def frequency_equalizer_chart(mel_spec, sr, accent="#00d4ff"):
    """
    Create equalizer-style visualization from mel-spectrogram.

    Args:
        mel_spec: Mel-spectrogram (n_mels x time_frames)
        sr: Sample rate
        accent: Accent color for visualization

    Returns:
        Plotly figure object
    """
    # 1. Aggregate mel bins into 10-12 frequency bands
    # 2. Create frequency band labels (e.g., "125 Hz", "250 Hz", etc.)
    # 3. Create heatmap with time on x-axis, frequency bands on y-axis
    # 4. Use custom color scale from dark to accent
    # 5. Apply plotly_dark template
    # 6. Set height to 400px
    # 7. Return plotly figure
```

#### 4. Update Step 2 UI
**File:** `frontend/streamlit_app/src/ml-app.py`

**Function:** `stage_feature_analysis(analysis_result: dict | None)`

**New implementation:**
```python
def stage_feature_analysis(analysis_result: dict | None):
    with st.container(border=True):
        st.markdown("#### Stage 2 · Feature Analysis")
        if analysis_result is None:
            st.info("Complete Stage 1 to visualize features.")
            return

        # Extract visualization data from backend response
        viz_data = analysis_result.get("features", {})

        # Primary: Frequency Band Equalizer
        st.markdown("##### 🎵 Audio Frequency Spectrum")
        st.plotly_chart(
            frequency_equalizer_chart(
                mel_spec=viz_data["mel_spectrogram"],
                sample_rate=viz_data.get("sample_rate", 22050)
            ),
            use_container_width=True
        )

        # Secondary: 78-Feature Vector Table
        st.markdown("##### 🔢 Model Input Features (78 MFCC-based features)")
        st.caption("These are the exact features extracted and fed into the ML model.")
        st.dataframe(
            pd.DataFrame(viz_data["feature_table"]),
            use_container_width=True,
            hide_index=True,
            height=400
        )

        # Prediction button (results already available, just navigate)
        if st.button("🚀 View Prediction Results", key="view-results-btn"):
            st.session_state[TAB_INDEX_KEY] = 2
            st.rerun()
```

## Files to Modify

### Backend Files:
1. **`backend/models/v2/feature_extractor.py`**
   - Add: `extract_features_with_visualization_data()` function

2. **`backend/app/services/model_registry.py`**
   - Add: `extract_features_with_viz()` method

3. **`backend/app/api/v1/endpoints/inference_local.py`**
   - Add: `POST /infer/local/{version}/analyze` endpoint

### Frontend Files:
4. **`frontend/streamlit_app/src/api_client.py`** or **`real_inference.py`**
   - Add: `analyze_with_features()` method

5. **`frontend/streamlit_app/src/ml-app.py`**
   - Remove: `_generate_local_features()` function
   - Add: `_call_backend_analyze_api()` function
   - Update: `stage_audio_recording()` to call backend
   - Update: `stage_feature_analysis()` for new visualizations

6. **`frontend/streamlit_app/src/feature_charts.py`**
   - Add: `frequency_equalizer_chart()` function

## Testing Plan

### Unit Tests
- [ ] Test `extract_features_with_visualization_data()` returns correct structure
- [ ] Test feature vector has 78 dimensions
- [ ] Test mel-spectrogram shape is correct
- [ ] Test feature breakdown has 78 entries

### Integration Tests
- [ ] Test `/v1/infer/local/2/analyze` endpoint with valid audio file
- [ ] Test endpoint returns both predictions and features
- [ ] Test frontend API client correctly calls endpoint
- [ ] Test frontend correctly parses backend response

### End-to-End Tests
1. Launch Streamlit app on port 8510
2. Upload sample audio file (WAV, MP3, M4A)
3. Verify Step 1 completes successfully
4. Navigate to Step 2
5. Verify Step 2 displays:
   - Frequency equalizer with time/frequency axes
   - 78-feature table with MFCC, Delta, Delta² features
   - No old features (RMS, Spectral Centroid, etc.)
6. Click "View Prediction Results"
7. Verify Step 3 displays correct emotion prediction
8. Monitor logs for 15 seconds for errors

### Performance Tests
- [ ] Measure API response time for feature extraction
- [ ] Verify no duplicate feature extraction
- [ ] Check memory usage during visualization rendering

## Benefits

### Technical Benefits:
1. **Separation of Concerns** - Backend handles extraction, frontend visualizes
2. **Single Source of Truth** - Features extracted once, used for viz + inference
3. **Consistency** - Same extraction logic for display and model
4. **Performance** - No duplicate feature extraction
5. **Maintainability** - Changes only in backend

### User Experience Benefits:
6. **Model Alignment** - Shows exact 78 features model uses
7. **Visual Appeal** - Intuitive equalizer visualization
8. **Transparency** - See both visual (equalizer) and exact input (table)
9. **Educational** - Understand MFCC-based feature extraction
10. **Professional** - Consistent dark theme styling
11. **Holistic Coverage** - Visual + detailed numerical features

## Dependencies

### Backend:
- `librosa>=0.11.0` (already installed)
- `numpy>=1.24.0` (already installed)
- `fastapi>=0.104.0` (already installed)

### Frontend:
- `plotly>=6.5.0` (already installed)
- `pandas>=2.0.0` (already installed)
- `streamlit>=1.51.0` (already installed)

No new dependencies required.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Backend API latency | High | Add caching for repeated audio files |
| Large mel-spectrogram data transfer | Medium | Compress data or reduce resolution |
| Frontend rendering performance | Medium | Use Plotly optimization techniques |
| Breaking changes to existing flow | High | Comprehensive testing, phased rollout |

## Success Metrics

- [ ] Step 2 displays only model-relevant features
- [ ] API response time < 500ms for typical audio files
- [ ] Zero frontend feature extraction (confirmed via code review)
- [ ] 100% test coverage for new backend functions
- [ ] User feedback: visualization helps understand model behavior

## Timeline Estimate

- Backend feature extractor enhancement: **2 hours**
- Backend API endpoint: **2 hours**
- Frontend chart function: **2 hours**
- Frontend UI updates: **2 hours**
- Testing and bug fixes: **2 hours**
- **Total: ~10 hours**

## Related User Stories

- US-001: Model deployment API (provides base inference infrastructure)
- US-002: Streamlit frontend (provides UI foundation)
- Future: US-006: Feature importance visualization (could extend this work)

## References

- Model v2 Feature Extractor: `backend/models/v2/feature_extractor.py`
- Model v2 Metadata: `backend/models/v2/metadata.json`
- Existing Charts: `frontend/streamlit_app/src/feature_charts.py`
- CREMA-D Dataset Documentation: Project CLAUDE.md
