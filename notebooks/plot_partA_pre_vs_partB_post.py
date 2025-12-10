"""
Plot a comparison of Part A pre–hyperparameter tuning vs Part B post–hyperparameter tuning.

- Part A (pre-tuning): uses baseline test accuracies from
  `part_a_model_comparison_summary.csv`.
- Part B (post-tuning): uses tuned accuracies for individual models only
  (no stacking or Ultra ensembles), as in the Part B hyperparameter tuning:
    * SVM (poly), Random Forest, Logistic Regression, Naive Bayes (Gaussian),
      K-Nearest Neighbors → best mean_test_score from corresponding
      `*_cv_results.json`.
    * Extra Trees, Gradient Boosting → accuracy from their classification
      report CSVs.

Output: Project/partA_pre_vs_partB_post.png
"""

from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd


def load_part_a_pre(base: Path) -> pd.DataFrame:
    """Load Part A pre-tuning baseline test accuracies."""
    path = base / "part_a_model_comparison_summary.csv"
    df = pd.read_csv(path)
    df_pre = df[["Model", "Test Accuracy"]].rename(columns={"Test Accuracy": "Accuracy"})
    df_pre["Phase"] = "Part A (pre-tuned)"
    return df_pre


def best_mean_test_score(json_path: Path) -> float:
    """Return best mean_test_score from a RandomizedSearchCV cv_results_ JSON."""
    with json_path.open() as f:
        data = json.load(f)
    scores = data["mean_test_score"]
    return float(max(scores))


def load_part_b_post(base: Path) -> pd.DataFrame:
    """
    Load Part B post-tuning accuracies for individual models (no stacking).
    """
    rows = []

    # Models tuned via RandomizedSearchCV (JSON cv_results_)
    json_mapping = {
        "SVM (poly)": "svm_cv_results.json",
        "Random Forest": "rf_cv_results.json",
        "Naive Bayes (Gaussian)": "nb_cv_results.json",
        "Logistic Regression": "lr_cv_results.json",
        "K-Nearest Neighbors": "knn_cv_results.json",
    }
    for model_name, filename in json_mapping.items():
        path = base / filename
        if not path.exists():
            continue
        acc = best_mean_test_score(path)
        rows.append({"Model": model_name, "Accuracy": acc, "Phase": "Part B (post-tuned)"})

    # Models with classification reports (Extra Trees, Gradient Boosting)
    report_mapping = {
        "Extra Trees": "part_b_extra_trees_classification_report.csv",
        "Gradient Boosting": "part_b_gradient_boosting_classification_report.csv",
    }
    for model_name, filename in report_mapping.items():
        path = base / filename
        if not path.exists():
            continue
        report = pd.read_csv(path)
        acc_row = report.loc[report["label"] == "accuracy"].iloc[0]
        accuracy = float(acc_row["precision"])
        rows.append({"Model": model_name, "Accuracy": accuracy, "Phase": "Part B (post-tuned)"})

    return pd.DataFrame(rows)


def main() -> None:
    base = Path(__file__).resolve().parent

    df_pre = load_part_a_pre(base)
    df_post = load_part_b_post(base)

    df = pd.concat([df_pre, df_post], ignore_index=True)
    df["Accuracy (%)"] = df["Accuracy"] * 100.0

    # Sort by accuracy for readability
    df_sorted = df.sort_values("Accuracy (%)", ascending=True)

    # Label rows so that same model in different phases appears on separate lines.
    # Use short tags (A) and (B) for the y-axis, the legend still carries full text.
    def label_for_row(row: pd.Series) -> str:
        phase_tag = "A" if "Part A" in row["Phase"] else "B"
        return f"{row['Model']} ({phase_tag})"

    df_sorted["Label"] = df_sorted.apply(label_for_row, axis=1)

    phase_colors = {
        "Part A (pre-tuned)": "steelblue",
        "Part B (post-tuned)": "darkorange",
    }
    colors = df_sorted["Phase"].map(phase_colors)

    fig, ax = plt.subplots(figsize=(11, 8))
    bars = ax.barh(df_sorted["Label"], df_sorted["Accuracy (%)"], color=colors)

    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Model Performance: Part A Pre-Tuning vs Part B Post-Tuning")

    for bar, acc in zip(bars, df_sorted["Accuracy (%)"]):
        ax.text(
            acc + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{acc:.1f}",
            va="center",
            ha="left",
            fontsize=9,
        )

    handles = [
        plt.Line2D([0], [0], color=color, lw=10, label=phase)
        for phase, color in phase_colors.items()
    ]
    ax.legend(handles=handles, title="Phase", loc="lower right")

    fig.tight_layout()
    out_path = base / "partA_pre_vs_partB_post.png"
    fig.savefig(out_path, dpi=300)
    print(f"Saved Part A pre vs Part B post comparison plot to: {out_path}")


if __name__ == "__main__":
    main()
