"""
Configure Compact Evidently Dashboard with Grid Layout

Creates a space-efficient dashboard with 2-column grid layout.
Size guide: size="half" creates 50% width panels (2 columns), size="full" creates 100% width

Usage:
    poetry run python scripts/configure_compact_dashboard.py
"""

from pathlib import Path
from evidently.ui.workspace import Workspace
from evidently.sdk.models import DashboardPanelPlot, PanelMetric

# Setup
BACKEND_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BACKEND_DIR / "evidently_workspace"
EMOTIONS = ["angry", "disgust", "fear", "happy", "neutral", "sad"]

print("=" * 80)
print("Configuring Compact Grid Dashboard")
print("=" * 80)

# Load workspace
ws = Workspace.create(str(WORKSPACE_DIR))
project = ws.search_project("speech_emotion_recognition")[0]
print(f"✅ Project: {project.id}")

# Clear and rebuild
project.dashboard.clear_dashboard()

# ============================================================================
# ROW 1: KEY METRICS (2 columns)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Accuracy",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:Accuracy", metric_labels={"classification_name": "default"}, legend="Accuracy")],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Precision",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:Precision", metric_labels={"classification_name": "default"}, legend="Precision")],
        plot_params={"plot_type": "counter"}
    )
)

# ============================================================================
# ROW 2: MORE KEY METRICS (2 columns)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Recall",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:Recall", metric_labels={"classification_name": "default"}, legend="Recall")],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="F1 Score",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:F1Score", metric_labels={"classification_name": "default"}, legend="F1")],
        plot_params={"plot_type": "counter"}
    )
)

# ============================================================================
# ROW 3: PERFORMANCE TREND (full width)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Performance Over Time",
        size="full",
        values=[
            PanelMetric(metric="evidently:metric_v2:Accuracy", metric_labels={"classification_name": "default"}, legend="Accuracy"),
            PanelMetric(metric="evidently:metric_v2:Precision", metric_labels={"classification_name": "default"}, legend="Precision"),
            PanelMetric(metric="evidently:metric_v2:Recall", metric_labels={"classification_name": "default"}, legend="Recall"),
            PanelMetric(metric="evidently:metric_v2:F1Score", metric_labels={"classification_name": "default"}, legend="F1")
        ],
        plot_params={"plot_type": "line"}
    )
)

# Note: Per-class metrics removed to prevent OOM issues
# Only aggregated classification metrics are available

# ============================================================================
# ROW 8: DRIFT METRICS (2 columns)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Drifted Features (%)",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:DriftedColumnsCount", metric_labels={"value_type": "share"}, legend="Drift %")],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Drifted Features (#)",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:DriftedColumnsCount", metric_labels={"value_type": "count"}, legend="Count")],
        plot_params={"plot_type": "counter"}
    )
)

# ============================================================================
# ROW 5: PREDICTION & LABEL DRIFT (2 columns)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Drift (p-value)",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:ValueDrift", metric_labels={"column": "predicted_emotion"}, legend="Pred Drift")],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Label Drift (p-value)",
        size="half",
        values=[PanelMetric(metric="evidently:metric_v2:ValueDrift", metric_labels={"column": "actual_emotion"}, legend="Label Drift")],
        plot_params={"plot_type": "counter"}
    )
)

# ============================================================================
# ROW 6: DRIFT TRENDS OVER TIME (full width)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Drift Trends Over Time",
        size="full",
        values=[
            PanelMetric(metric="evidently:metric_v2:DriftedColumnsCount", metric_labels={"value_type": "share"}, legend="Feature Drift %"),
            PanelMetric(metric="evidently:metric_v2:ValueDrift", metric_labels={"column": "predicted_emotion"}, legend="Prediction Drift"),
            PanelMetric(metric="evidently:metric_v2:ValueDrift", metric_labels={"column": "actual_emotion"}, legend="Label Drift"),
        ],
        plot_params={"plot_type": "line"}
    )
)

# ============================================================================
# ROW 11: CONCEPT DRIFT (full width performance degradation)
# ============================================================================

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Concept Drift Detection: Performance Degradation",
        subtitle="Sustained drops indicate concept drift",
        size="full",
        values=[
            PanelMetric(metric="evidently:metric_v2:Accuracy", metric_labels={"classification_name": "default"}, legend="Accuracy"),
            PanelMetric(metric="evidently:metric_v2:F1Score", metric_labels={"classification_name": "default"}, legend="F1")
        ],
        plot_params={"plot_type": "line"}
    )
)

project.save()

print(f"\n✅ 2-Column Grid Dashboard Configured!")
print(f"\n📊 Layout (2-column grid with size='half'):")
print(f"   • Row 1: Accuracy + Precision (counters)")
print(f"   • Row 2: Recall + F1 Score (counters)")
print(f"   • Row 3: Performance Over Time (full width line plot)")
print(f"   • Row 4: Drifted Features % + # (counters)")
print(f"   • Row 5: Prediction Drift + Label Drift (counters)")
print(f"   • Row 6: Drift Trends Over Time (full width line plot)")
print(f"   • Row 7: Concept Drift Detection (full width line plot)")
print(f"\n   Total: 11 panels in 2-column grid layout")
print(f"\n   Drift Metrics Available:")
print(f"      • Dataset Drift: evidently:metric_v2:DriftedColumnsCount")
print(f"      • Prediction Drift: evidently:metric_v2:ValueDrift (column=predicted_emotion)")
print(f"      • Label Drift: evidently:metric_v2:ValueDrift (column=actual_emotion)")
print(f"\n🌐 Access: http://localhost:8080/projects/{project.id}")
print(f"\n💡 Refresh browser (F5) to see the updated layout")
print("=" * 80)
