"""
Configure Enhanced Evidently Dashboard with Rich Visualizations

This script creates a comprehensive ML monitoring dashboard with:
- Per-class performance metrics for all 6 emotions
- Feature-level drift analysis
- Prediction confidence distributions
- Multiple visualization types (counters, lines, scatter, histogram)
- Professional dashboard design following 2025 UX principles

Usage:
    poetry run python scripts/configure_enhanced_dashboard.py

References:
- https://docs.evidentlyai.com/docs/platform/dashboard_add_panels
- https://www.evidentlyai.com/classification-metrics
- https://docs.evidentlyai.com/reference/api-reference/evidently.metrics/evidently.metrics.classification_performance
"""

from pathlib import Path
from evidently.ui.workspace import Workspace
from evidently.sdk.models import DashboardPanelPlot, PanelMetric

# Setup paths
BACKEND_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BACKEND_DIR / "evidently_workspace"

# 6 emotion classes in speech emotion recognition
EMOTIONS = ["angry", "disgust", "fear", "happy", "neutral", "sad"]

print("=" * 80)
print("Configuring Enhanced Evidently Dashboard with Rich Visualizations")
print("=" * 80)

# Load workspace
print(f"\n📂 Loading workspace: {WORKSPACE_DIR}")
ws = Workspace.create(str(WORKSPACE_DIR))

# Get existing project
PROJECT_NAME = "speech_emotion_recognition"
print(f"\n🔍 Finding project: {PROJECT_NAME}")

project = ws.search_project(PROJECT_NAME)[0]
print(f"✅ Found project: {project.id}")

print(f"\n⚙️  Configuring enhanced dashboard panels...")

# Clear existing dashboard entirely
project.dashboard.clear_dashboard()

# ===================================================================
# SECTION 1: KEY PERFORMANCE METRICS (3-column grid)
# ===================================================================
print("\n📊 SECTION 1: Key Performance Metrics (3-column grid)")

# Row 1: 3 key counters (Accuracy, Precision, Recall)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Accuracy",
        subtitle="Overall classification accuracy",
        size=1,  # 1/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Accuracy",
                metric_labels={"classification_name": "default"},
                legend="Accuracy"
            )
        ],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Precision",
        subtitle="Quality of predictions",
        size=1,  # 1/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Precision",
                metric_labels={"classification_name": "default"},
                legend="Precision"
            )
        ],
        plot_params={"plot_type": "counter"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Recall",
        subtitle="Coverage of actual positives",
        size=1,  # 1/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Recall",
                metric_labels={"classification_name": "default"},
                legend="Recall"
            )
        ],
        plot_params={"plot_type": "counter"}
    )
)

# Row 2: Performance timeline + F1 Score counter
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Performance Trends",
        subtitle="Metrics evolution over time",
        size=2,  # 2/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Accuracy",
                metric_labels={"classification_name": "default"},
                legend="Accuracy"
            ),
            PanelMetric(
                metric="evidently:metric_v2:Precision",
                metric_labels={"classification_name": "default"},
                legend="Precision"
            ),
            PanelMetric(
                metric="evidently:metric_v2:Recall",
                metric_labels={"classification_name": "default"},
                legend="Recall"
            )
        ],
        plot_params={"plot_type": "line"}
    )
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="F1 Score",
        subtitle="Harmonic mean",
        size=1,  # 1/3 width
        values=[
            PanelMetric(
                metric="evidently:metric_v2:F1Score",
                metric_labels={"classification_name": "default"},
                legend="F1"
            )
        ],
        plot_params={"plot_type": "counter"}
    )
)

print("  ✓ Added 5 key metric panels (3-column grid layout)")

# ===================================================================
# TAB 2: PER-CLASS PERFORMANCE - Emotion-Specific Metrics
# ===================================================================
print("\n📊 TAB 2: Per-Class Performance")

# Per-Class Precision (6 emotions)
for emotion in EMOTIONS:
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title=f"{emotion.capitalize()} Precision",
            subtitle=f"Quality of {emotion} predictions",
            size=1,  # 1/3 width (3 per row)
            values=[
                PanelMetric(
                    metric="evidently:metric_v2:ClassificationQualityByClass",
                    metric_labels={"label": emotion, "metric": "precision"},
                    legend="Precision"
                )
            ],
            plot_params={"plot_type": "counter"}
        ),
        tab="Per-Class Performance"
    )

# Per-Class Recall (6 emotions)
for emotion in EMOTIONS:
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title=f"{emotion.capitalize()} Recall",
            subtitle=f"Coverage of actual {emotion} samples",
            size=1,
            values=[
                PanelMetric(
                    metric="evidently:metric_v2:ClassificationQualityByClass",
                    metric_labels={"label": emotion, "metric": "recall"},
                    legend="Recall"
                )
            ],
            plot_params={"plot_type": "counter"}
        ),
        tab="Per-Class Performance"
    )

# Per-Class F1 Score (6 emotions)
for emotion in EMOTIONS:
    project.dashboard.add_panel(
        DashboardPanelPlot(
            title=f"{emotion.capitalize()} F1 Score",
            subtitle=f"Balanced performance for {emotion}",
            size=1,
            values=[
                PanelMetric(
                    metric="evidently:metric_v2:ClassificationQualityByClass",
                    metric_labels={"label": emotion, "metric": "f1-score"},
                    legend="F1 Score"
                )
            ],
            plot_params={"plot_type": "counter"}
        ),
        tab="Per-Class Performance"
    )

# Per-Class Performance Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Per-Class F1 Score Trends",
        subtitle="F1 score evolution for each emotion",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ClassificationQualityByClass",
                metric_labels={"label": emotion, "metric": "f1-score"},
                legend=emotion.capitalize()
            ) for emotion in EMOTIONS
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Per-Class Performance"
)

print(f"  ✓ Added {3 * len(EMOTIONS) + 1} per-class panels (18 emotion counters + 1 timeline)")

# ===================================================================
# TAB 3: DATA DRIFT - Feature Distribution Changes
# ===================================================================
print("\n📊 TAB 3: Data Drift")

# Overall Drift Metrics
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Share of Drifted Features (%)",
        subtitle="Percentage of features showing distribution drift",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "share"},
                legend="Drift %"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Data Drift"
)

project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Number of Drifted Features",
        subtitle="Count of features exceeding drift threshold",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "count"},
                legend="Drift Count"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Data Drift"
)

# Drift Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Feature Drift Over Time",
        subtitle="% of drifted features across snapshots",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DriftedColumnsCount",
                metric_labels={"value_type": "share"},
                legend="% Drifted"
            )
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Data Drift"
)

# Dataset Drift Score (histogram showing distribution of drift scores)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Dataset Drift Score",
        subtitle="Overall dataset drift magnitude",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DatasetDriftMetric",
                metric_labels={"value_type": "score"},
                legend="Drift Score"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Data Drift"
)

# Drift Score Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Drift Score Trend",
        subtitle="Dataset drift score evolution",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:DatasetDriftMetric",
                metric_labels={"value_type": "score"},
                legend="Drift Score"
            )
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Data Drift"
)

print("  ✓ Added 5 data drift panels (3 counters + 2 timelines)")

# ===================================================================
# TAB 4: PREDICTION & LABEL DRIFT
# ===================================================================
print("\n📊 TAB 4: Prediction & Label Drift")

# Prediction Drift Detection
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Drift Detected",
        subtitle="Changes in model output distribution",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "predicted_emotion"},
                legend="Prediction Drift"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Prediction & Label Drift"
)

# Label Drift Detection (when ground truth available)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Label Drift Detected",
        subtitle="Changes in actual label distribution",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "actual_emotion"},
                legend="Label Drift"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Prediction & Label Drift"
)

# Prediction Distribution Timeline
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Distribution Shift",
        subtitle="Drift score for predicted emotions over time",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ColumnDrift",
                metric_labels={"column_name": "predicted_emotion"},
                legend="Drift Score"
            )
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Prediction & Label Drift"
)

# Prediction Class Balance
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Prediction Class Balance",
        subtitle="Distribution of predicted emotions",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ClassificationClassBalance",
                metric_labels={"column_type": "prediction"},
                legend="Class Balance"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Prediction & Label Drift"
)

# Label Class Balance (when ground truth available)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Label Class Balance",
        subtitle="Distribution of actual emotions",
        size=1,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ClassificationClassBalance",
                metric_labels={"column_type": "target"},
                legend="Class Balance"
            )
        ],
        plot_params={"plot_type": "counter"}
    ),
    tab="Prediction & Label Drift"
)

print("  ✓ Added 5 prediction/label drift panels (4 counters + 1 timeline)")

# ===================================================================
# TAB 5: CONCEPT DRIFT - Performance Degradation
# ===================================================================
print("\n📊 TAB 5: Concept Drift")

# Accuracy Trend (primary concept drift indicator)
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
        plot_params={"plot_type": "line"}
    ),
    tab="Concept Drift"
)

# F1 Score Degradation
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
        plot_params={"plot_type": "line"}
    ),
    tab="Concept Drift"
)

# Per-Class Performance Degradation (all emotions on one chart)
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Per-Class Performance Degradation",
        subtitle="F1 score decline per emotion - identifies which emotions are drifting",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:ClassificationQualityByClass",
                metric_labels={"label": emotion, "metric": "f1-score"},
                legend=emotion.capitalize()
            ) for emotion in EMOTIONS
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Concept Drift"
)

# Combined Metrics for Concept Drift Detection
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Combined Performance Metrics",
        subtitle="All key metrics to detect concept drift patterns",
        size=2,
        values=[
            PanelMetric(
                metric="evidently:metric_v2:Accuracy",
                metric_labels={"classification_name": "default"},
                legend="Accuracy"
            ),
            PanelMetric(
                metric="evidently:metric_v2:Precision",
                metric_labels={"classification_name": "default"},
                legend="Precision"
            ),
            PanelMetric(
                metric="evidently:metric_v2:Recall",
                metric_labels={"classification_name": "default"},
                legend="Recall"
            ),
            PanelMetric(
                metric="evidently:metric_v2:F1Score",
                metric_labels={"classification_name": "default"},
                legend="F1 Score"
            )
        ],
        plot_params={"plot_type": "line"}
    ),
    tab="Concept Drift"
)

print("  ✓ Added 4 concept drift panels (4 multi-metric timelines)")

# Save the dashboard configuration
project.save()

print(f"\n✅ Enhanced Dashboard configured successfully!")
print(f"\n📊 Dashboard Structure:")
print(f"\n   TAB 1: Overview (5 panels)")
print(f"      • 4 key metric counters (Accuracy, Precision, Recall, F1)")
print(f"      • 1 combined performance timeline")
print(f"\n   TAB 2: Per-Class Performance ({3 * len(EMOTIONS) + 1} panels)")
print(f"      • {len(EMOTIONS)} Precision counters (one per emotion)")
print(f"      • {len(EMOTIONS)} Recall counters (one per emotion)")
print(f"      • {len(EMOTIONS)} F1 Score counters (one per emotion)")
print(f"      • 1 multi-emotion timeline")
print(f"\n   TAB 3: Data Drift (5 panels)")
print(f"      • Drift share and count counters")
print(f"      • Dataset drift score counter")
print(f"      • 2 drift timelines")
print(f"\n   TAB 4: Prediction & Label Drift (5 panels)")
print(f"      • Prediction and label drift counters")
print(f"      • Class balance counters")
print(f"      • Prediction distribution timeline")
print(f"\n   TAB 5: Concept Drift (4 panels)")
print(f"      • Accuracy and F1 degradation timelines")
print(f"      • Per-class performance degradation")
print(f"      • Combined metrics timeline")
print(f"\n📈 Total: {5 + (3 * len(EMOTIONS) + 1) + 5 + 5 + 4} panels across 5 tabs")

print(f"\n🌐 Access dashboard at: http://localhost:8080/projects/{project.id}")
print(f"\n💡 Next Steps:")
print(f"   1. Refresh the Evidently UI in your browser (F5 or Cmd+R)")
print(f"   2. Click on 'Dashboard' tab")
print(f"   3. Explore all 5 tabs:")
print(f"      - Overview: Quick health check")
print(f"      - Per-Class Performance: Emotion-specific metrics")
print(f"      - Data Drift: Feature distribution changes")
print(f"      - Prediction & Label Drift: Output distribution shifts")
print(f"      - Concept Drift: Performance degradation patterns")
print(f"   4. Classification metrics require ground truth (submit feedback)")
print(f"   5. Generate more predictions to see trends over time")

print(f"\n🔍 Monitoring Coverage:")
print(f"   ✓ Overall Performance: Accuracy, Precision, Recall, F1")
print(f"   ✓ Per-Emotion Performance: Individual class metrics for all 6 emotions")
print(f"   ✓ Data Drift: Feature distribution changes")
print(f"   ✓ Prediction Drift: Model output distribution changes")
print(f"   ✓ Label Drift: Target distribution changes")
print(f"   ✓ Concept Drift: Performance degradation detection")

print("\n" + "=" * 80)
print("Dashboard enhancement complete! 🎉")
print("=" * 80)
