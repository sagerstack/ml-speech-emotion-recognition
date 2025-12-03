"""
Setup Evidently workspace with proper structure for UI dashboard

This script creates a workspace with projects and adds reports as snapshots.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, ClassificationPreset, TargetDriftPreset
from evidently.ui.workspace import Workspace
from evidently.ui.dashboards import CounterAgg, DashboardPanelCounter, PanelValue, ReportFilter

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BACKEND_DIR / "evidently_workspace"
REPORTS_DIR = BACKEND_DIR / "monitoring_reports"

print("🔧 Setting up Evidently workspace for UI dashboard...")
print(f"   Workspace location: {WORKSPACE_DIR}")

# Load the test data we generated earlier
reference_csv = REPORTS_DIR / "test_reference_data.csv"
current_csv = REPORTS_DIR / "test_current_data.csv"

if not reference_csv.exists() or not current_csv.exists():
    print(f"❌ Test data not found. Run test_evidently_dashboard.py first.")
    exit(1)

print(f"📊 Loading test data...")
reference_df = pd.read_csv(reference_csv)
current_df = pd.read_csv(current_csv)

print(f"   Reference: {len(reference_df)} samples")
print(f"   Current: {len(current_df)} samples")

# Create workspace
print(f"\n🏗️  Creating workspace...")
if WORKSPACE_DIR.exists():
    print(f"   Workspace already exists, using existing: {WORKSPACE_DIR}")
    ws = Workspace.create(str(WORKSPACE_DIR))
else:
    ws = Workspace.create(str(WORKSPACE_DIR))
    print(f"   ✅ Workspace created: {WORKSPACE_DIR}")

# Create project
PROJECT_NAME = "speech_emotion_recognition"
PROJECT_DESC = "ML Speech Emotion Recognition Model Monitoring"

print(f"\n📁 Creating project: {PROJECT_NAME}")
try:
    project = ws.create_project(PROJECT_NAME)
    project.description = PROJECT_DESC
    project.save()
    print(f"   ✅ Project created")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"   Project already exists, using existing")
        project = ws.get_project(PROJECT_NAME)
    else:
        raise

# Identify feature columns (exclude metadata)
META_COLUMNS = {'timestamp', 'model_version', 'predicted_emotion', 'actual_emotion', 'confidence', 'filename'}
all_columns = set(reference_df.columns)
probability_columns = {col for col in all_columns if col.startswith('proba_')}
feature_columns = list(all_columns - META_COLUMNS - probability_columns)

print(f"\n📈 Feature columns: {len(feature_columns)}")
print(f"   Probability columns: {len(probability_columns)}")

# Configure column mapping
column_mapping = ColumnMapping(
    target='actual_emotion',
    prediction='predicted_emotion',
    numerical_features=feature_columns,
)

# Create and run report
print(f"\n🔄 Generating report snapshot...")
report = Report(metrics=[
    DataDriftPreset(),
    ClassificationPreset(),
    TargetDriftPreset(),
])

report.run(
    reference_data=reference_df,
    current_data=current_df,
    column_mapping=column_mapping
)

# Add report to project as snapshot
print(f"   Adding report to project...")
ws.add_report(project.id, report)

print(f"\n✅ Workspace setup complete!")
print(f"\n🎉 Next steps:")
print(f"   1. Launch Evidently UI:")
print(f"      cd backend && poetry run evidently ui --workspace evidently_workspace --host 0.0.0.0 --port 8080")
print(f"   2. Access dashboard: http://localhost:8080")
print(f"   3. You should see the '{PROJECT_NAME}' project with 1 snapshot")
