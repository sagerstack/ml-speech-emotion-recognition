# US-006 Testing Guide

## Quick Start

### Prerequisites
1. Backend running at http://127.0.0.1:8000
2. Sample audio file: `data/AudioWAV/1001_DFA_ANG_XX.wav`
3. Browser with network inspector (Chrome DevTools)

### Launch Application

```bash
# Terminal 1: Start backend
cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/frontend/streamlit_app/src
streamlit run ml-app.py --server.port 8510

# Browser: Open http://localhost:8510
```

---

## Test Scenarios

### Scenario 1: Real Backend with Angry Emotion ✅

**Setup:**
- Backend: Running
- Mock Mode: OFF (unchecked in sidebar)
- Audio File: `1001_DFA_ANG_XX.wav` (angry emotion)

**Steps:**
1. Open http://localhost:8510
2. Upload `data/AudioWAV/1001_DFA_ANG_XX.wav`
3. Click "🚀 Analyze Audio"
4. Wait for Tab 1 completion
5. Click Tab 2 to view features
6. Click "🚀 Predict Emotion"
7. Navigate to Tab 3

**Expected Results:**

| Element | Expected Value | Actual | ✓/✗ |
|---------|---------------|--------|-----|
| Material Icon | sentiment_very_dissatisfied (angry face) | | |
| Emotion Name | "Angry" | | |
| Confidence | "100%" | | |
| Processing Time | "~59 ms" (varies) | | |
| Model Version | "v2" | | |
| Performance Color | Green (if <100ms) | | |
| Performance Label | "Fast" | | |
| Model Name | "SVM with MFCC Features" | | |
| Architecture | "Pipeline (StandardScaler + RFE + SVC)" | | |
| Feature Extraction | "MFCCs with delta and delta-delta coefficients" | | |
| Feature Dimension | "78" | | |
| Training Dataset | "CREMA-D" | | |
| Created Date | "2024-01-20" | | |
| Emotion Classes | "angry, disgust, fear, happy, neutral, sad" | | |
| Description | "Support Vector Machine..." | | |
| Notes | "Improved model with feature selection..." | | |
| Progress Bar | Green bar with white text | | |
| Legend | Three colored bullets (green, yellow, red) | | |
| Probability Chart | All 6 emotions displayed | | |
| Detailed Table | Sorted by confidence, angry at top | | |
| Trophy Icon | Appears only on "Angry" row | | |

**Screenshots to Capture:**
- [ ] Full Tab 3 view (entire page)
- [ ] Hero section (emotion icon + name)
- [ ] Metrics row (3 metrics)
- [ ] Two-column cards (Model Info + Description)
- [ ] Performance metrics with green bar
- [ ] Probability chart
- [ ] Detailed scores table

---

### Scenario 2: Real Backend with Happy Emotion ✅

**Setup:**
- Backend: Running
- Mock Mode: OFF
- Audio File: Find a file with happy emotion (or use mock mode)

**Steps:**
1. Upload happy emotion audio file
2. Complete workflow through Tab 3

**Expected Results:**

| Element | Expected Value |
|---------|---------------|
| Material Icon | sentiment_very_satisfied (happy face) |
| Emotion Name | "Happy" |
| Confidence | High % (depends on file) |
| Icon Color | Pink (#be185d) |

---

### Scenario 3: Mock Mode Enabled 🔵

**Setup:**
- Backend: Running or Not Running
- Mock Mode: ON (checked in sidebar)

**Steps:**
1. Toggle "Enable Mock Mode" in sidebar
2. Upload any audio file
3. Complete workflow to Tab 3

**Expected Results:**

| Element | Expected Value |
|---------|---------------|
| API Status | "🔵 Mock Mode (Forced)" |
| Emotion | "Happy" |
| Confidence | "95%" |
| Processing Time | "45.32 ms" |
| Model Version | "v2" |
| Performance Color | Green (Fast) |
| All other fields | Should populate with mock data |

**Verification:**
- Open browser DevTools → Network tab
- Verify NO API call to `/v1/models/local/latest`
- All data should be from `get_mock_model_metadata()`

---

### Scenario 4: Backend Unavailable (Fallback) ⚠️

**Setup:**
- Backend: STOPPED (kill backend process)
- Mock Mode: OFF

**Steps:**
1. Stop backend: `pkill -f uvicorn`
2. Upload audio file
3. Try to analyze

**Expected Results:**

| Element | Expected Value |
|---------|---------------|
| API Status | "❌ Backend Unavailable" or "🟡 Using Mock (Fallback)" |
| Behavior | App should NOT crash |
| Data Source | Falls back to mock metadata |
| Error Handling | Graceful degradation |

**Logs to Check:**
```bash
# Check Streamlit logs for warnings
tail -f /tmp/streamlit_us006.log | grep -i "warning\|error"
```

Expected log entries:
- "Failed to fetch metadata: HTTP 500" or
- "Connection error" or
- "Request timeout"

---

### Scenario 5: Performance Color Verification 🎨

**Objective:** Test all three performance color categories

#### 5a. Fast Processing (<100ms) - GREEN

**Audio File:** Small file (short duration)

**Expected:**
- Progress bar color: `#10b981` (green)
- Performance label: "Fast"
- Processing time: <100ms

#### 5b. Medium Processing (100-500ms) - YELLOW

**Audio File:** Medium file or simulate slow processing

**Expected:**
- Progress bar color: `#f59e0b` (yellow/orange)
- Performance label: "Medium"
- Processing time: 100-499ms

#### 5c. Slow Processing (≥500ms) - RED

**Audio File:** Large file or simulate very slow processing

**Expected:**
- Progress bar color: `#ef4444` (red)
- Performance label: "Slow"
- Processing time: ≥500ms

**How to Simulate Slow Processing:**
If you need to test slow performance without large files, you can temporarily modify the backend to add artificial delay:

```python
# In backend inference function (for testing only)
import time
time.sleep(0.6)  # Add 600ms delay
```

---

### Scenario 6: Responsive Layout 📱

**Objective:** Test layout on different screen sizes

**Steps:**
1. Open Tab 3 with results displayed
2. Open browser DevTools (F12)
3. Toggle device toolbar (Ctrl+Shift+M)
4. Test different screen sizes

#### Desktop (>1024px)
**Expected:**
- Two columns side-by-side
- Cards have equal width
- All content visible

#### Tablet (768px-1024px)
**Expected:**
- Two columns still side-by-side
- Slightly narrower
- Text wraps appropriately

#### Mobile (<768px)
**Expected:**
- Cards stack vertically
- Model Info card appears first
- Description card appears below
- Full width utilization

---

### Scenario 7: All Emotion Icons 🎭

**Objective:** Verify each emotion displays correct Material icon

Test each emotion systematically:

| Emotion | Expected Icon Name | Visual | File to Test |
|---------|-------------------|--------|--------------|
| angry | sentiment_very_dissatisfied | 😞 | 1001_DFA_ANG_XX.wav |
| disgust | sick | 🤢 | *_DIS_*.wav |
| fear | sentiment_stressed | 😰 | *_FEA_*.wav |
| happy | sentiment_very_satisfied | 😃 | *_HAP_*.wav |
| neutral | sentiment_neutral | 😐 | *_NEU_*.wav |
| sad | sentiment_dissatisfied | 😔 | *_SAD_*.wav |

**Steps for Each:**
1. Upload audio file for specific emotion
2. Complete workflow to Tab 3
3. Verify icon matches expected visual
4. Check icon name in browser inspector:
   - Right-click icon → Inspect Element
   - Look for `<span class="material-symbols-rounded">`
   - Verify inner text matches icon name

---

### Scenario 8: Data Accuracy Verification 🔍

**Objective:** Ensure all data matches backend response

**Steps:**
1. Open browser DevTools → Network tab
2. Upload audio and analyze
3. Navigate to Tab 3
4. Find API call: `GET .../v1/models/local/latest`
5. Click to view response

**Compare Response to Display:**

| API Field | Display Location | Match? |
|-----------|-----------------|--------|
| `version` | Model Version metric | ✓/✗ |
| `model_name` | Model Info card | ✓/✗ |
| `model_type` | Architecture field | ✓/✗ |
| `feature_extraction` | Feature Extraction field | ✓/✗ |
| `feature_dimension` | Feature Dimension field | ✓/✗ |
| `dataset` | Training Dataset field | ✓/✗ |
| `created_date` | Created Date field | ✓/✗ |
| `classes` | Emotion Classes field (comma-separated) | ✓/✗ |
| `description` | Description card text | ✓/✗ |
| `notes` | Notes section text | ✓/✗ |

**Example API Response:**
```json
{
  "version": "2",
  "model_name": "SVM with MFCC Features",
  "model_type": "Pipeline (StandardScaler + RFE + SVC)",
  "description": "Support Vector Machine with MFCC-based features and Recursive Feature Elimination",
  "feature_dimension": 78,
  "feature_extraction": "MFCCs with delta and delta-delta coefficients",
  "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
  "num_classes": 6,
  "created_date": "2024-01-20",
  "dataset": "CREMA-D",
  "notes": "Improved model with feature selection and SVM classifier"
}
```

---

### Scenario 9: Error Handling 🚨

**Objective:** Verify app doesn't crash on errors

#### 9a. Invalid Backend URL

**Setup:**
```bash
export ML_APP_BASE_URL=http://invalid-host:9999
streamlit run ml-app.py --server.port 8510
```

**Expected:**
- App starts normally
- API status shows error
- Falls back to mock data
- No Python exceptions

#### 9b. Network Timeout

**Setup:**
- Configure extremely slow network
- Or modify timeout to 1 second

**Expected:**
- Timeout after 5 seconds
- Logs show "Request timeout"
- Falls back to mock data

#### 9c. Malformed API Response

**Setup:**
- Temporarily break backend to return invalid JSON

**Expected:**
- Logs show parsing error
- App falls back to mock data
- User sees mock results (not crash)

---

### Scenario 10: Performance Benchmark ⏱️

**Objective:** Measure UI render time

**Tools:**
- Browser DevTools → Performance tab
- Lighthouse audit

**Steps:**
1. Open Tab 3 with results
2. Start Performance recording
3. Navigate away and back to Tab 3
4. Stop recording
5. Analyze rendering time

**Acceptance Criteria:**
- Total render time < 500ms ✅
- No blocking scripts > 100ms
- Smooth scrolling performance

**Lighthouse Audit:**
1. Right-click page → Inspect
2. Lighthouse tab
3. Run audit (Desktop)
4. Check Performance score

**Target Scores:**
- Performance: >90
- Accessibility: >90
- Best Practices: >90

---

## Regression Testing Checklist

Verify existing functionality still works:

- [ ] Tab 1: Audio upload works
- [ ] Tab 1: Audio recording works
- [ ] Tab 1: Engine selection works
- [ ] Tab 2: Features display correctly
- [ ] Tab 2: All visualizations render
- [ ] Tab 2: Predict button works
- [ ] Tab 3: Probability chart displays
- [ ] Tab 3: Detailed scores table displays
- [ ] Sidebar: Backend status indicator updates
- [ ] Sidebar: Mock mode toggle works
- [ ] Sidebar: API health test button works
- [ ] History page: Previous analyses saved
- [ ] History page: Data displays correctly
- [ ] Metrics page: Metrics display (if applicable)

---

## Bug Reporting Template

If you find issues during testing, use this template:

```markdown
## Bug Report

**Scenario:** [e.g., Scenario 1: Real Backend with Angry Emotion]

**Steps to Reproduce:**
1. ...
2. ...
3. ...

**Expected Result:**
[What should happen]

**Actual Result:**
[What actually happened]

**Screenshots:**
[Attach screenshots]

**Browser Console Errors:**
```
[Paste any console errors]
```

**Environment:**
- Browser: [Chrome/Firefox/Safari version]
- OS: [macOS/Windows/Linux]
- Backend Status: [Running/Not Running]
- Mock Mode: [ON/OFF]

**Severity:**
- [ ] Critical (app crashes)
- [ ] High (major feature broken)
- [ ] Medium (minor feature issue)
- [ ] Low (cosmetic issue)

**Additional Context:**
[Any other relevant information]
```

---

## Test Results Log

Use this table to track your testing progress:

| Scenario | Date | Tester | Pass/Fail | Notes |
|----------|------|--------|-----------|-------|
| 1. Real Backend - Angry | | | | |
| 2. Real Backend - Happy | | | | |
| 3. Mock Mode | | | | |
| 4. Backend Unavailable | | | | |
| 5a. Fast Performance | | | | |
| 5b. Medium Performance | | | | |
| 5c. Slow Performance | | | | |
| 6. Responsive Layout | | | | |
| 7. All Emotion Icons | | | | |
| 8. Data Accuracy | | | | |
| 9a. Invalid URL | | | | |
| 9b. Network Timeout | | | | |
| 9c. Malformed Response | | | | |
| 10. Performance Benchmark | | | | |
| Regression Tests | | | | |

---

## Automated Testing Commands

### Quick Health Check:
```bash
# Test backend is running
curl -s http://127.0.0.1:8000/health | jq

# Test metadata endpoint
curl -s http://127.0.0.1:8000/v1/models/local/latest | jq

# Test frontend is accessible
curl -s http://localhost:8510 | grep -q "Speech Emotion" && echo "✓ Frontend OK"
```

### Load Testing (Optional):
```bash
# Test multiple concurrent requests
for i in {1..10}; do
  curl -s http://127.0.0.1:8000/v1/models/local/latest &
done
wait
echo "Load test complete"
```

### Log Monitoring:
```bash
# Monitor frontend logs
tail -f /tmp/streamlit_us006.log

# Monitor backend logs (if using uvicorn directly)
tail -f uvicorn.log

# Search for errors
grep -i "error\|exception\|warning" /tmp/streamlit_us006.log
```

---

## Sign-Off

Once all tests pass, complete this sign-off:

**Tested By:** ___________________
**Date:** ___________________
**Environment:** Production / Staging / Local
**Overall Result:** ✅ PASS / ❌ FAIL

**Summary:**
- Total Scenarios Tested: ___
- Scenarios Passed: ___
- Scenarios Failed: ___
- Bugs Found: ___

**Recommendation:**
- [ ] Ready for Production
- [ ] Needs Minor Fixes
- [ ] Needs Major Fixes
- [ ] Needs Redesign

**Approver Signature:** ___________________

---

**Document Version:** 1.0
**Last Updated:** 2025-11-30
**Next Review:** After bug fixes or feature updates
