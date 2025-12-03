"""
Test script to generate sample Evidently report and launch dashboard

This creates dummy prediction data to demonstrate Evidently features
before we generate real reference data from CREMA-D.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
REPORTS_DIR = BACKEND_DIR / "monitoring_reports"
REPORTS_DIR.mkdir(exist_ok=True)

print("🎯 Generating test data for Evidently dashboard...")

# Generate synthetic reference data (training baseline)
np.random.seed(42)
n_samples = 500

emotions = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']

# Generate 78 MFCC features
feature_names = []
for i in range(1, 14):
    feature_names.extend([f'mfcc_{i}_mean', f'mfcc_{i}_std'])
for i in range(1, 14):
    feature_names.extend([f'mfcc_delta_{i}_mean', f'mfcc_delta_{i}_std'])
for i in range(1, 14):
    feature_names.extend([f'mfcc_delta2_{i}_mean', f'mfcc_delta2_{i}_std'])

print(f"📊 Creating reference dataset with {len(feature_names)} features...")

# Reference data (baseline - well-behaved distribution)
reference_data = {
    'timestamp': [datetime.now() - timedelta(days=30, hours=i) for i in range(n_samples)],
    'model_version': ['2'] * n_samples,
    'predicted_emotion': np.random.choice(emotions, n_samples),
    'actual_emotion': np.random.choice(emotions, n_samples),
    'confidence': np.random.uniform(0.7, 0.95, n_samples),
    'filename': [f'audio_{i}.wav' for i in range(n_samples)],
}

# Generate features with specific distributions
for feature in feature_names:
    reference_data[feature] = np.random.normal(loc=-10, scale=5, size=n_samples)

# Add probabilities
for emotion in emotions:
    reference_data[f'proba_{emotion}'] = np.random.dirichlet(np.ones(6), size=n_samples)[:, emotions.index(emotion)]

reference_df = pd.DataFrame(reference_data)

print(f"✅ Reference data: {len(reference_df)} samples")
print(f"   Columns: {len(reference_df.columns)}")
print(f"   Emotions: {reference_df['predicted_emotion'].value_counts().to_dict()}")

# Current data (production - some drift)
current_data = {
    'timestamp': [datetime.now() - timedelta(hours=i) for i in range(100)],
    'model_version': ['2'] * 100,
    'predicted_emotion': np.random.choice(emotions, 100, p=[0.3, 0.1, 0.1, 0.2, 0.2, 0.1]),  # Drift: more angry
    'actual_emotion': np.random.choice(emotions, 100),
    'confidence': np.random.uniform(0.6, 0.85, 100),  # Lower confidence
    'filename': [f'prod_audio_{i}.wav' for i in range(100)],
}

# Generate features with DRIFT (shifted distribution)
for feature in feature_names:
    current_data[feature] = np.random.normal(loc=-8, scale=6, size=100)  # Shifted mean and higher variance

# Add probabilities
for emotion in emotions:
    current_data[f'proba_{emotion}'] = np.random.dirichlet(np.ones(6), size=100)[:, emotions.index(emotion)]

current_df = pd.DataFrame(current_data)

print(f"✅ Current data: {len(current_df)} samples")
print(f"   Emotions: {current_df['predicted_emotion'].value_counts().to_dict()}")

# Generate Evidently report
print("\n📈 Generating Evidently report...")

try:
    from evidently import ColumnMapping
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, ClassificationPreset, TargetDriftPreset

    # Configure column mapping
    column_mapping = ColumnMapping(
        target='actual_emotion',
        prediction='predicted_emotion',
        numerical_features=feature_names,
    )

    # Create report with multiple presets
    report = Report(metrics=[
        DataDriftPreset(),
        ClassificationPreset(),
        TargetDriftPreset(),
    ])

    print("🔄 Running report generation...")
    report.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping
    )

    # Save HTML report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = REPORTS_DIR / f"test_report_{timestamp}.html"
    json_path = REPORTS_DIR / f"test_report_{timestamp}.json"

    report.save_html(str(html_path))
    report.save_json(str(json_path))

    print(f"\n✅ Report generated successfully!")
    print(f"   HTML: {html_path}")
    print(f"   JSON: {json_path}")

    # Save reference and current data for inspection
    reference_csv = REPORTS_DIR / "test_reference_data.csv"
    current_csv = REPORTS_DIR / "test_current_data.csv"

    reference_df.to_csv(reference_csv, index=False)
    current_df.to_csv(current_csv, index=False)

    print(f"\n📁 Test data saved:")
    print(f"   Reference: {reference_csv}")
    print(f"   Current: {current_csv}")

    print(f"\n🎉 Success! Now you can:")
    print(f"   1. Open HTML report: open {html_path}")
    print(f"   2. Launch Evidently UI: cd backend && poetry run evidently ui --workspace monitoring_reports --port 8080")
    print(f"   3. Access dashboard: http://localhost:8080")

except Exception as e:
    print(f"\n❌ Error generating report: {e}")
    import traceback
    traceback.print_exc()
