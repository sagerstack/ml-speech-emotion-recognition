"""
Configure Comprehensive Evidently Dashboard using Python API

This script uses Evidently's Python API to properly configure dashboard panels
for classification metrics and drift monitoring.

Usage:
    poetry run python scripts/configure_rich_dashboard.py
"""

from pathlib import Path
from evidently.ui.workspace import Workspace
from evidently.sdk.models import DashboardPanelPlot, PanelMetric

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BACKEND_DIR / "evidently_workspace"

print("=" * 80)
print("Configuring Comprehensive Evidently Dashboard (Python API)")
print("=" * 80)

# Load workspace
print(f"\n📂 Loading workspace: {WORKSPACE_DIR}")
ws = Workspace.create(str(WORKSPACE_DIR))

# Get existing project
PROJECT_NAME = "speech_emotion_recognition"
print(f"\n🔍 Finding project: {PROJECT_NAME}")

project = ws.search_project(PROJECT_NAME)[0]
print(f"✅ Found project: {project.id}")

print(f"\n⚙️  Configuring dashboard panels...")

# Clear existing dashboard entirely
project.dashboard.clear_dashboard()

# ===================================================================
# TAB 1: CLASSIFICATION METRICS
# ===================================================================

# Panel 1: Accuracy Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Model Accuracy",
        size=1,  # 1/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Accuracy",
                metric_labels={"classification_name": "default"},
                legend="Accuracy"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added accuracy counter")

# Panel 2: Precision Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Model Precision",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Precision",
                metric_labels={"classification_name": "default"},
                legend="Precision"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added precision counter")

# Panel 3: Recall Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Model Recall",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Recall",
                metric_labels={"classification_name": "default"},
                legend="Recall"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added recall counter")

# Panel 4: Accuracy Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Accuracy Over Time",
        size=2,  # full width
        values=[
            PanelMetric(
                metric="Accuracy",
                legend="Accuracy"
            )
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added accuracy timeline")

# Panel 5: F1 Score Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="F1 Score",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:F1Score",
                metric_labels={"classification_name": "default"},
                legend="F1"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added F1 score counter")

# Panel 6: Combined Metrics Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Classification Metrics Trend",
        size=2,
        values=[
            PanelMetric(metric="evidently:metric_v2:Precision", metric_labels={"classification_name": "default"}, legend="Precision"),
            PanelMetric(metric="evidently:metric_v2:Recall", metric_labels={"classification_name": "default"}, legend="Recall"),
            PanelMetric(metric="evidently:metric_v2:F1Score", metric_labels={"classification_name": "default"}, legend="F1")
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Classification Metrics"
)
print("  ✓ Added combined metrics timeline")

# ===================================================================
# TAB 2: DATA DRIFT
# ===================================================================

# Panel 7: Drift Share Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Share of Drifted Features (%)",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "share"},
                legend="Drift %"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Data Drift"
)
print("  ✓ Added drift share counter")

# Panel 8: Drift Count Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Number of Drifted Features",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "count"},
                legend="Drift Count"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Data Drift"
)
print("  ✓ Added drift count counter")

# Panel 9: Drift Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Drift Share Over Time",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "share"},
                legend="% Drifted"
            )
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Data Drift"
)
print("  ✓ Added drift timeline")

# ===================================================================
# TAB 3: PREDICTION & LABEL DRIFT
# ===================================================================

# Panel 10: Prediction Drift Counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Drift Detected",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "predicted_emotion"},
                legend="Prediction Drift"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Prediction & Label Drift"
)
print("  ✓ Added prediction drift counter")

# Panel 11: Label Drift Counter (when ground truth available)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Label Drift Detected",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "actual_emotion"},
                legend="Label Drift"
            )
        ],
        plot_params={
            "plot_type": "counter"
        }
    ),
    tab="Prediction & Label Drift"
)
print("  ✓ Added label drift counter")

# Panel 12: Prediction Distribution Over Time
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Distribution Shift",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "predicted_emotion"},
                legend="Drift Score"
            )
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Prediction & Label Drift"
)
print("  ✓ Added prediction distribution timeline")

# ===================================================================
# TAB 4: CONCEPT DRIFT (ACCURACY DEGRADATION)
# ===================================================================

# Panel 13: Concept Drift Indicator (Accuracy Drop)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Concept Drift: Accuracy Trend",
        subtitle="Sustained accuracy drops indicate concept drift",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Accuracy",
                metric_labels={"classification_name": "default"},
                legend="Accuracy"
            )
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Concept Drift"
)
print("  ✓ Added concept drift indicator")

# Panel 14: F1 Score Degradation
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Model Performance Degradation",
        subtitle="F1 Score decline over time",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:F1Score",
                metric_labels={"classification_name": "default"},
                legend="F1 Score"
            )
        ],
        plot_params={
            "plot_type": "line"
        }
    ),
    tab="Concept Drift"
)
print("  ✓ Added F1 degradation indicator")

# Save the dashboard configuration
project.save()

print(f"\n✅ Dashboard configured successfully!")
print(f"\n📊 Dashboard Structure:")
print(f"\n   TAB 1: Classification Metrics (6 panels)")
print(f"      • Accuracy, Precision, Recall counters")
print(f"      • F1 score counter")
print(f"      • Accuracy timeline")
print(f"      • Combined metrics timeline")
print(f"\n   TAB 2: Data Drift (3 panels)")
print(f"      • Drift share counter (%)")
print(f"      • Drift count counter (#)")
print(f"      • Drift timeline")
print(f"\n   TAB 3: Prediction & Label Drift (3 panels)")
print(f"      • Prediction drift counter")
print(f"      • Label drift counter")
print(f"      • Prediction distribution timeline")
print(f"\n   TAB 4: Concept Drift (2 panels)")
print(f"      • Accuracy degradation timeline")
print(f"      • F1 score degradation timeline")

print(f"\n🌐 Access dashboard at: http://localhost:8080/projects/{project.id}")
print(f"\n💡 Next Steps:")
print(f"   1. Refresh the Evidently UI in your browser")
print(f"   2. Click on 'Dashboard' tab")
print(f"   3. View all 4 tabs: Classification, Data Drift, Prediction/Label Drift, Concept Drift")
print(f"   4. Classification metrics require ground truth (submit feedback)")
print(f"   5. Generate more predictions to see trends over time")
print(f"\n🔍 Drift Monitoring Coverage:")
print(f"   ✓ Data Drift: Feature distribution changes (Tab 2)")
print(f"   ✓ Prediction Drift: Model output changes (Tab 3)")
print(f"   ✓ Label Drift: Target distribution changes (Tab 3)")
print(f"   ✓ Concept Drift: Performance degradation (Tab 4)")
print("=" * 80)
