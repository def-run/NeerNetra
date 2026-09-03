"""
NeerNetra — Model Evaluator
==============================
Comprehensive evaluation metrics for flood prediction models.

Required metrics (Section 6.7):
  - Precision
  - Recall
  - F1-score
  - ROC-AUC
  - PR-AUC
  - Confusion matrix

"For disaster prediction, recall for dangerous flood events is
 particularly important, but increasing recall may increase false alarms."

Also reports:
  - Feature importance ranking
  - Per-class metrics
  - Threshold analysis
"""

import numpy as np
from typing import Optional

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
    precision_recall_curve,
    roc_curve,
)


class ModelEvaluator:
    """
    Evaluates flood prediction models with comprehensive metrics.
    """

    def evaluate(
        self,
        model,
        X: np.ndarray,
        y_true: np.ndarray,
        feature_names: Optional[list] = None,
        dataset_name: str = "Test",
    ) -> dict:
        """
        Run full evaluation on a dataset.

        Args:
            model: Trained sklearn model with predict() and predict_proba()
            X: Feature matrix
            y_true: True labels
            feature_names: Feature names for importance ranking
            dataset_name: Label for this evaluation (e.g., "Test", "Validation")

        Returns:
            dict with all metrics
        """
        y_pred = model.predict(X)
        y_prob = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else y_pred.astype(float)

        metrics = self._compute_metrics(y_true, y_pred, y_prob)
        cm = confusion_matrix(y_true, y_pred)

        # Feature importance
        importance = self._get_feature_importance(model, feature_names)

        results = {
            "dataset": dataset_name,
            "metrics": metrics,
            "confusion_matrix": cm.tolist(),
            "feature_importance": importance,
            "n_samples": len(y_true),
            "n_positive": int(y_true.sum()),
            "n_negative": int((1 - y_true).sum()),
        }

        return results

    def print_report(self, results: dict):
        """Print a formatted evaluation report."""
        metrics = results["metrics"]
        cm = results["confusion_matrix"]
        importance = results.get("feature_importance", [])

        print(f"\n{'='*60}")
        print(f"  Model Evaluation — {results['dataset']}")
        print(f"{'='*60}")
        print(f"  Samples: {results['n_samples']} "
              f"(Positive: {results['n_positive']}, Negative: {results['n_negative']})")
        print()

        # Core metrics
        print("  Metrics:")
        print(f"    Precision:  {metrics['precision']:.4f}")
        print(f"    Recall:     {metrics['recall']:.4f}")
        print(f"    F1-Score:   {metrics['f1']:.4f}")
        print(f"    ROC-AUC:    {metrics['roc_auc']:.4f}")
        print(f"    PR-AUC:     {metrics['pr_auc']:.4f}")
        print(f"    Accuracy:   {metrics['accuracy']:.4f}")
        print()

        # Confusion matrix
        print("  Confusion Matrix:")
        print(f"                  Predicted")
        print(f"                  No Flood  Flood")
        print(f"    Actual No Flood  {cm[0][0]:>6}  {cm[0][1]:>6}")
        print(f"    Actual Flood     {cm[1][0]:>6}  {cm[1][1]:>6}")
        print()

        # False alarm analysis
        if cm[0][1] + cm[1][1] > 0:
            false_alarm_rate = cm[0][1] / (cm[0][0] + cm[0][1]) if (cm[0][0] + cm[0][1]) > 0 else 0
            miss_rate = cm[1][0] / (cm[1][0] + cm[1][1]) if (cm[1][0] + cm[1][1]) > 0 else 0
            print(f"  False Alarm Rate: {false_alarm_rate:.4f}")
            print(f"  Miss Rate:        {miss_rate:.4f}")
            print()

        # Top features
        if importance:
            print("  Top 10 Most Important Features:")
            for i, (name, score) in enumerate(importance[:10], 1):
                bar = "#" * int(score * 50)
                print(f"    {i:>2}. {name:<35} {score:.4f} {bar}")

        print(f"\n{'='*60}")

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------
    @staticmethod
    def _compute_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
    ) -> dict:
        """Compute all evaluation metrics."""
        return {
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
            "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
            "accuracy": round(float(np.mean(y_true == y_pred)), 4),
        }

    @staticmethod
    def _get_feature_importance(
        model,
        feature_names: Optional[list] = None,
    ) -> list:
        """
        Extract feature importance from the model.

        Returns sorted list of (feature_name, importance_score) tuples.
        """
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_[0])
        else:
            return []

        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(importances))]

        pairs = list(zip(feature_names, importances))
        pairs.sort(key=lambda x: x[1], reverse=True)

        return [(name, round(float(score), 6)) for name, score in pairs]
