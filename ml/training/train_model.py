"""
NeerNetra — Model Training Pipeline
=======================================
Trains and compares flood prediction models.

From Section 6.2:
  Primary MVP: Random Forest Classifier
  Advanced: XGBoost Classifier
  Baseline: Logistic Regression

Training process (Section 6.5):
  1. Generate / load dataset
  2. Temporal train/val/test split (Section 6.6)
  3. Build feature matrices
  4. Train baseline (Logistic Regression)
  5. Train Random Forest
  6. Train XGBoost
  7. Evaluate all models (Section 6.7)
  8. Save the best model

"Do not claim XGBoost is better until it has actually been evaluated."
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.data.dataset_generator import generate_dataset, save_dataset
from ml.features.feature_builder import FeatureBuilder, ALL_FEATURES
from ml.preprocessing.data_splitter import temporal_split
from ml.evaluation.evaluator import ModelEvaluator
from ml.training.model_registry import ModelRegistry


def train_all_models(
    n_samples: int = 5000,
    flood_ratio: float = 0.15,
    seed: int = 42,
) -> dict:
    """
    Run the complete model training pipeline.

    Returns:
        dict with results for all models
    """
    print("=" * 60)
    print("  NeerNetra — Flood Prediction Model Training")
    print("=" * 60)

    # -----------------------------------------------------------------
    # 1. Generate dataset
    # -----------------------------------------------------------------
    print("\n[1/7] Generating training dataset...")
    df = generate_dataset(n_samples=n_samples, flood_ratio=flood_ratio, seed=seed)

    dataset_path = os.path.join("data", "processed", "training_dataset.csv")
    save_dataset(df, dataset_path)

    # -----------------------------------------------------------------
    # 2. Temporal split
    # -----------------------------------------------------------------
    print("\n[2/7] Splitting data (temporal)...")
    train_df, val_df, test_df = temporal_split(df)

    # -----------------------------------------------------------------
    # 3. Build features
    # -----------------------------------------------------------------
    print("\n[3/7] Building feature matrices...")
    builder = FeatureBuilder()

    X_train, y_train = builder.prepare_features(train_df, fit_scaler=True)
    X_val, y_val = builder.prepare_features(val_df)
    X_test, y_test = builder.prepare_features(test_df)

    feature_names = builder.get_feature_names()
    print(f"  Features: {len(feature_names)}")
    print(f"  X_train: {X_train.shape}, X_val: {X_val.shape}, X_test: {X_test.shape}")

    # -----------------------------------------------------------------
    # 4-6. Train models
    # -----------------------------------------------------------------
    evaluator = ModelEvaluator()
    registry = ModelRegistry()
    all_results = {}

    # --- Baseline: Logistic Regression ---
    print("\n[4/7] Training Baseline (Logistic Regression)...")
    lr_model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
        solver="lbfgs",
    )
    lr_model.fit(X_train, y_train)

    lr_val = evaluator.evaluate(lr_model, X_val, y_val, feature_names, "Validation")
    lr_test = evaluator.evaluate(lr_model, X_test, y_test, feature_names, "Test")
    evaluator.print_report(lr_test)

    all_results["logistic_regression"] = {
        "model": lr_model,
        "val_metrics": lr_val["metrics"],
        "test_metrics": lr_test["metrics"],
        "test_results": lr_test,
    }

    # --- Primary: Random Forest ---
    print("\n[5/7] Training Random Forest (MVP Model)...")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    rf_model.fit(X_train, y_train)

    rf_val = evaluator.evaluate(rf_model, X_val, y_val, feature_names, "Validation")
    rf_test = evaluator.evaluate(rf_model, X_test, y_test, feature_names, "Test")
    evaluator.print_report(rf_test)

    all_results["random_forest"] = {
        "model": rf_model,
        "val_metrics": rf_val["metrics"],
        "test_metrics": rf_test["metrics"],
        "test_results": rf_test,
    }

    # --- Advanced: XGBoost ---
    if HAS_XGBOOST:
        print("\n[6/7] Training XGBoost (Advanced)...")

        # Compute scale_pos_weight for imbalanced data
        n_neg = int((y_train == 0).sum())
        n_pos = int((y_train == 1).sum())
        scale_pos = n_neg / n_pos if n_pos > 0 else 1.0

        xgb_model = XGBClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            scale_pos_weight=scale_pos,
            random_state=seed,
            eval_metric="logloss",
            use_label_encoder=False,
        )
        xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        xgb_val = evaluator.evaluate(xgb_model, X_val, y_val, feature_names, "Validation")
        xgb_test = evaluator.evaluate(xgb_model, X_test, y_test, feature_names, "Test")
        evaluator.print_report(xgb_test)

        all_results["xgboost"] = {
            "model": xgb_model,
            "val_metrics": xgb_val["metrics"],
            "test_metrics": xgb_test["metrics"],
            "test_results": xgb_test,
        }
    else:
        print("\n[6/7] XGBoost not installed — skipping.")

    # -----------------------------------------------------------------
    # 7. Compare and select best model
    # -----------------------------------------------------------------
    print("\n[7/7] Model Comparison:")
    print(f"\n  {'Model':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'ROC-AUC':>10} {'PR-AUC':>10}")
    print("  " + "-" * 75)

    best_model_name = None
    best_f1 = -1

    for name, result in all_results.items():
        m = result["test_metrics"]
        label = name.replace("_", " ").title()
        print(f"  {label:<25} {m['precision']:>10.4f} {m['recall']:>10.4f} "
              f"{m['f1']:>10.4f} {m['roc_auc']:>10.4f} {m['pr_auc']:>10.4f}")

        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_model_name = name

    print(f"\n  ✓ Best model: {best_model_name} (F1 = {best_f1:.4f})")

    # -----------------------------------------------------------------
    # 8. Save models
    # -----------------------------------------------------------------
    print("\n  Saving models...")

    for name, result in all_results.items():
        registry.save_model(
            model=result["model"],
            model_name=f"flood_{name}",
            model_type=name,
            metrics=result["test_metrics"],
            feature_names=feature_names,
            scaler_params=builder.scaler_params,
            hyperparameters=_get_hyperparams(result["model"]),
        )

    # Save comparison report
    comparison = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_size": n_samples,
        "flood_ratio": flood_ratio,
        "best_model": best_model_name,
        "results": {
            name: result["test_metrics"]
            for name, result in all_results.items()
        },
    }
    report_path = os.path.join("ml", "saved_models", "comparison_report.json")
    with open(report_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n  Comparison report: {report_path}")

    print(f"\n{'='*60}")
    print(f"  Training complete. Best model: {best_model_name}")
    print(f"{'='*60}")

    return all_results


def _get_hyperparams(model) -> dict:
    """Extract hyperparameters from a model."""
    try:
        params = model.get_params()
        # Only keep serializable params
        clean = {}
        for k, v in params.items():
            if isinstance(v, (int, float, str, bool, type(None))):
                clean[k] = v
        return clean
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    train_all_models(n_samples=5000, flood_ratio=0.15)
