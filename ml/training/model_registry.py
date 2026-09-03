"""
NeerNetra — Model Registry
==============================
Save, load, and manage trained ML models with metadata.

Serializes models using joblib along with:
  - Feature names and scaler parameters
  - Training metrics
  - Model type and hyperparameters
  - Timestamp and version info
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional

import joblib
import numpy as np


MODELS_DIR = os.path.join("ml", "saved_models")


class ModelRegistry:
    """
    Manages model persistence with metadata.
    """

    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)

    def save_model(
        self,
        model,
        model_name: str,
        model_type: str,
        metrics: dict,
        feature_names: list,
        scaler_params: Optional[dict] = None,
        hyperparameters: Optional[dict] = None,
    ) -> str:
        """
        Save a trained model with metadata.

        Args:
            model: Trained sklearn model
            model_name: Name for the saved model file
            model_type: Type string (e.g., "random_forest", "xgboost")
            metrics: Evaluation metrics dict
            feature_names: Ordered list of feature names
            scaler_params: Optional scaler parameters (mean, std)
            hyperparameters: Optional model hyperparameters

        Returns:
            Path to saved model file
        """
        # Save model
        model_path = os.path.join(self.models_dir, f"{model_name}.joblib")
        joblib.dump(model, model_path)

        # Save metadata
        metadata = {
            "model_name": model_name,
            "model_type": model_type,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "feature_names": feature_names,
            "n_features": len(feature_names),
            "hyperparameters": hyperparameters or {},
        }

        # Save scaler params separately (numpy arrays)
        if scaler_params is not None:
            scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.joblib")
            joblib.dump(scaler_params, scaler_path)
            metadata["scaler_path"] = scaler_path

        meta_path = os.path.join(self.models_dir, f"{model_name}_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        print(f"Model saved: {model_path}")
        print(f"Metadata saved: {meta_path}")

        return model_path

    def load_model(self, model_name: str) -> tuple:
        """
        Load a saved model with its metadata and scaler.

        Args:
            model_name: Name of the saved model

        Returns:
            (model, metadata, scaler_params) tuple
        """
        model_path = os.path.join(self.models_dir, f"{model_name}.joblib")
        meta_path = os.path.join(self.models_dir, f"{model_name}_metadata.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        model = joblib.load(model_path)

        metadata = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                metadata = json.load(f)

        scaler_params = None
        scaler_path = os.path.join(self.models_dir, f"{model_name}_scaler.joblib")
        if os.path.exists(scaler_path):
            scaler_params = joblib.load(scaler_path)

        return model, metadata, scaler_params

    def list_models(self) -> list:
        """List all saved models."""
        models = []
        for f in os.listdir(self.models_dir):
            if f.endswith("_metadata.json"):
                name = f.replace("_metadata.json", "")
                meta_path = os.path.join(self.models_dir, f)
                with open(meta_path, "r") as fh:
                    meta = json.load(fh)
                models.append({
                    "name": name,
                    "type": meta.get("model_type"),
                    "saved_at": meta.get("saved_at"),
                    "f1": meta.get("metrics", {}).get("f1"),
                    "roc_auc": meta.get("metrics", {}).get("roc_auc"),
                })
        return models

    def get_best_model(self, metric: str = "f1") -> Optional[str]:
        """
        Get the name of the best model by a given metric.

        Args:
            metric: Metric to compare (default: f1)

        Returns:
            Model name or None
        """
        models = self.list_models()
        if not models:
            return None

        best = max(models, key=lambda m: m.get(metric, 0) or 0)
        return best["name"]
