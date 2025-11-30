# Tab 3: Results Redesign - Layout Diagram

## Visual Layout Overview

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                 Stage 3 · Inference Results                     ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃                                                                  ┃
┃                    ### Primary Emotion                           ┃
┃                                                                  ┃
┃                    ┌──────────────────┐                          ┃
┃                    │                  │                          ┃
┃                    │   😞 (Icon 80px)  │  ← Material Symbol     ┃
┃                    │                  │                          ┃
┃                    │      Angry       │  ← Emotion Name         ┃
┃                    │   (32px bold)    │                          ┃
┃                    └──────────────────┘                          ┃
┃                                                                  ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃                                                                  ┃
┃   ┌─────────────┬─────────────────┬─────────────────┐           ┃
┃   │ Confidence  │ Processing Time │  Model Version  │           ┃
┃   │    100%     │    59.27 ms     │       v2        │           ┃
┃   └─────────────┴─────────────────┴─────────────────┘           ┃
┃                                                                  ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃                                                                  ┃
┃   ┌─────────────────────────────┬──────────────────────────┐    ┃
┃   │  📊 Model Information       │  📝 Model Description    │    ┃
┃   │  ┌───────────────────────┐  │  ┌────────────────────┐  │    ┃
┃   │  │ Model Name:           │  │  │ Support Vector     │  │    ┃
┃   │  │ SVM with MFCC Features│  │  │ Machine with MFCC- │  │    ┃
┃   │  │                       │  │  │ based features and │  │    ┃
┃   │  │ Architecture:         │  │  │ Recursive Feature  │  │    ┃
┃   │  │ Pipeline (Standard-   │  │  │ Elimination        │  │    ┃
┃   │  │ Scaler + RFE + SVC)   │  │  │                    │  │    ┃
┃   │  │                       │  │  │ ───────────────── │  │    ┃
┃   │  │ Feature Extraction:   │  │  │ Notes:             │  │    ┃
┃   │  │ MFCCs with delta and  │  │  │ Improved model with│  │    ┃
┃   │  │ delta-delta coeff.    │  │  │ feature selection  │  │    ┃
┃   │  │                       │  │  │ and SVM classifier │  │    ┃
┃   │  │ Feature Dimension: 78 │  │  └────────────────────┘  │    ┃
┃   │  │                       │  │                          │    ┃
┃   │  │ Training Dataset:     │  │                          │    ┃
┃   │  │ CREMA-D               │  │                          │    ┃
┃   │  │                       │  │                          │    ┃
┃   │  │ Created Date:         │  │                          │    ┃
┃   │  │ 2024-01-20            │  │                          │    ┃
┃   │  │                       │  │                          │    ┃
┃   │  │ Emotion Classes:      │  │                          │    ┃
┃   │  │ angry, disgust, fear, │  │                          │    ┃
┃   │  │ happy, neutral, sad   │  │                          │    ┃
┃   │  └───────────────────────┘  │                          │    ┃
┃   └─────────────────────────────┴──────────────────────────┘    ┃
┃                                                                  ┃
┃   ┌────────────────────────────────────────────────────────┐    ┃
┃   │            ⚡ Performance Metrics                       │    ┃
┃   │  ┌──────────────────┬──────────────────────────────┐  │    ┃
┃   │  │ Processing Time  │  [████████          ] 59.27ms │  │    ┃
┃   │  │    59.27 ms      │  ← Green progress bar        │  │    ┃
┃   │  │                  │                               │  │    ┃
┃   │  │ Performance:     │  Legend:                      │  │    ┃
┃   │  │ Fast             │  ● Fast (<100ms)              │  │    ┃
┃   │  │                  │  ● Medium (100-500ms)         │  │    ┃
┃   │  │                  │  ● Slow (≥500ms)              │  │    ┃
┃   │  └──────────────────┴──────────────────────────────┘  │    ┃
┃   └────────────────────────────────────────────────────────┘    ┃
┃                                                                  ┃
┃   ┌────────────────────────────────────────────────────────┐    ┃
┃   │        🎭 Emotion Probability Distribution              │    ┃
┃   │                                                         │    ┃
┃   │   ██████████████████████████ angry   100%              │    ┃
┃   │   ██ disgust                  2.1%                     │    ┃
┃   │   █ fear                      1.2%                     │    ┃
┃   │   █ happy                     0.8%                     │    ┃
┃   │   █ neutral                   0.5%                     │    ┃
┃   │   █ sad                       0.3%                     │    ┃
┃   │                                                         │    ┃
┃   └────────────────────────────────────────────────────────┘    ┃
┃                                                                  ┃
┃   ┌────────────────────────────────────────────────────────┐    ┃
┃   │          📈 Detailed Emotion Scores                     │    ┃
┃   │                                                         │    ┃
┃   │  ┌─────────┬────────────┬────────────┬──────┐          │    ┃
┃   │  │ Emotion │ Confidence │ Percentage │Status│          │    ┃
┃   │  ├─────────┼────────────┼────────────┼──────┤          │    ┃
┃   │  │ Angry   │   1.000    │   100.0%   │  🏆  │          │    ┃
┃   │  │ Disgust │   0.021    │    2.1%    │      │          │    ┃
┃   │  │ Fear    │   0.012    │    1.2%    │      │          │    ┃
┃   │  │ Happy   │   0.008    │    0.8%    │      │          │    ┃
┃   │  │ Neutral │   0.005    │    0.5%    │      │          │    ┃
┃   │  │ Sad     │   0.003    │    0.3%    │      │          │    ┃
┃   │  └─────────┴────────────┴────────────┴──────┘          │    ┃
┃   └────────────────────────────────────────────────────────┘    ┃
┃                                                                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Component Breakdown

### 1. Hero Section (Centered)
- **Icon:** Material Symbols Rounded, 80px, brand pink color
- **Emotion Name:** 32px, bold, centered below icon
- **Layout:** 3-column layout with icon in center column

### 2. Metrics Row (3 Columns)
```
┌───────────────┬───────────────────┬────────────────┐
│  Confidence   │  Processing Time  │ Model Version  │
│     100%      │     59.27 ms      │      v2        │
└───────────────┴───────────────────┴────────────────┘
```

### 3. Two-Column Card Layout
```
┌────────────────────────────┬───────────────────────────┐
│  📊 Model Information      │  📝 Model Description     │
│  (7 fields in label:value) │  (Description + Notes)    │
│                            │                           │
│  • Model Name              │  Full paragraph text      │
│  • Architecture            │                           │
│  • Feature Extraction      │  ─────────────────────   │
│  • Feature Dimension       │  Notes section            │
│  • Training Dataset        │                           │
│  • Created Date            │                           │
│  • Emotion Classes         │                           │
└────────────────────────────┴───────────────────────────┘
```

### 4. Performance Metrics (Full Width)
```
┌─────────────────────────────────────────────────────┐
│            ⚡ Performance Metrics                    │
│                                                      │
│  Processing Time: 59.27 ms                          │
│  Performance: Fast                                  │
│                                                      │
│  [████████████░░░░░░░░░░░░░░░░░] 59.27 ms          │
│  ← Green bar (Fast <100ms)                          │
│                                                      │
│  Legend:                                            │
│  ● Fast (<100ms)   ● Medium (100-500ms)   ● Slow   │
└─────────────────────────────────────────────────────┘
```

### 5. Probability Chart (Full Width)
- Plotly horizontal bar chart
- All emotions sorted by confidence
- Yellow accent color (#facc15)

### 6. Detailed Scores Table (Full Width)
- Pandas DataFrame
- Columns: Emotion, Confidence, Percentage, Status
- Sorted by confidence (descending)
- Trophy icon (🏆) for primary emotion

## Color Scheme

### Brand Colors:
- **Primary Pink:** `#be185d` (icons, buttons)
- **Accent Yellow:** `#facc15` (charts)

### Performance Colors:
- **Green (Fast):** `#10b981` - Processing time < 100ms
- **Yellow (Medium):** `#f59e0b` - Processing time 100-500ms
- **Red (Slow):** `#ef4444` - Processing time ≥ 500ms

### Neutral Colors:
- **Background:** `#e5e7eb` (progress bar track)
- **Text Dark:** `#1f2937` (primary text)
- **Text Gray:** `#6b7280` (secondary text)

## Responsive Behavior

### Desktop (>768px):
```
┌─────────────────┬─────────────────┐
│  Model Info     │  Description    │
│  (Left Column)  │  (Right Column) │
└─────────────────┴─────────────────┘
```

### Mobile (<768px):
```
┌─────────────────┐
│  Model Info     │
│  (Stacked)      │
├─────────────────┤
│  Description    │
│  (Stacked)      │
└─────────────────┘
```

## Material Icon Reference

| Emotion   | Icon Name                     | Display |
|-----------|-------------------------------|---------|
| angry     | sentiment_very_dissatisfied   | 😞      |
| disgust   | sick                          | 🤢      |
| fear      | sentiment_stressed            | 😰      |
| happy     | sentiment_very_satisfied      | 😃      |
| neutral   | sentiment_neutral             | 😐      |
| sad       | sentiment_dissatisfied        | 😔      |
| surprised | sentiment_excited             | 😲      |
| calm      | sentiment_calm                | 😌      |

## CSS Classes Used

```css
/* Material Icon */
.material-symbols-rounded {
    font-family: 'Material Symbols Rounded' !important;
    font-size: 80px;
    color: #be185d;
}

/* Progress Bar Container */
background-color: #e5e7eb;
border-radius: 8px;
height: 24px;

/* Progress Bar Fill (Dynamic Color) */
background-color: {perf_color};  /* Green/Yellow/Red */
width: {progress_value}%;
height: 100%;
color: white;
font-weight: 600;
font-size: 12px;
```

## Data Flow

```
User Action (Upload → Analyze)
         ↓
Stage 1: Audio Capture
         ↓
Stage 2: Feature Analysis
         ↓
Backend API: POST /v1/infer/local/latest
         ↓
AnalysisResult stored in session_state
         ↓
User Navigates to Tab 3
         ↓
stage_inference_results() called
         ↓
┌─────────────────────────────────┐
│ 1. Check backend status         │
│ 2. Fetch metadata (API/mock)    │
│ 3. Extract emotion data          │
│ 4. Calculate performance color   │
│ 5. Render layout components     │
└─────────────────────────────────┘
         ↓
Tab 3 Displays Complete Results
```

## Implementation Details

### Key Functions:

1. **`get_emotion_icon(emotion: str) -> str`**
   - Input: "angry"
   - Output: "sentiment_very_dissatisfied"

2. **`get_performance_color(time_ms: float) -> tuple[str, str]`**
   - Input: 59.27
   - Output: ("#10b981", "Fast")

3. **`fetch_latest_model_metadata() -> dict | None`**
   - API Call: GET http://127.0.0.1:8000/v1/models/local/latest
   - Returns: Model metadata JSON or None

4. **`stage_inference_results(result: AnalysisResult | None)`**
   - Main rendering function
   - Orchestrates all layout components
   - Handles real/mock mode switching

### Component Structure:

```python
stage_inference_results(result)
├── Hero Section (3-column layout)
│   └── Material Icon + Emotion Name
├── Metrics Row (3-column layout)
│   ├── Confidence metric
│   ├── Processing Time metric
│   └── Model Version metric
├── Two-Column Layout
│   ├── Left Column
│   │   └── Model Information Card (7 fields)
│   └── Right Column
│       └── Model Description Card
├── Performance Metrics (Full Width)
│   └── Color-coded Progress Bar
├── Probability Distribution (Full Width)
│   └── Plotly Bar Chart
└── Detailed Scores Table (Full Width)
    └── DataFrame with all emotions
```

---

## Testing Checklist

Use this visual reference when manually testing:

- [ ] Hero icon matches emotion (use table above)
- [ ] Emotion name is capitalized and centered
- [ ] Three metrics displayed in equal columns
- [ ] Processing time shows milliseconds (not seconds)
- [ ] Two columns are equal width on desktop
- [ ] Left card has all 7 model info fields
- [ ] Right card shows description + notes
- [ ] Performance bar color matches time category
- [ ] Progress bar shows time value inside bar
- [ ] Legend shows three color categories
- [ ] Probability chart displays all emotions
- [ ] Detailed table sorted by confidence
- [ ] Trophy (🏆) appears on primary emotion only

---

**Reference Date:** 2025-11-30
**Implementation:** US-006: Tab 3 Results Redesign
