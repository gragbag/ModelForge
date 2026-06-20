"""
Model serving — load registered models from MLflow and run predictions.

Loading a model downloads its artifact, which is slow, so we CACHE loaded models
in memory keyed by (name, version). A second prediction for the same model reuses
the in-memory copy instead of re-downloading.
"""

from typing import Any

import mlflow
import pandas as pd

from app.core.config import settings

# In-memory cache: (model_name, model_version) -> loaded model.
_model_cache: dict[tuple[str, str], Any] = {}


def load_model(model_name: str, model_version: str) -> Any:
    """Load a registered model version from the MLflow Model Registry (cached)."""
    key = (model_name, model_version)
    if key not in _model_cache:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        # "models:/<name>/<version>" is MLflow's URI for a registered model version.
        _model_cache[key] = mlflow.pyfunc.load_model(f"models:/{model_name}/{model_version}")
    return _model_cache[key]


def predict_one(model: Any, features: dict[str, Any]) -> Any:
    """Run a single-row prediction. The model expects the SAME feature columns it
    was trained on; pandas builds a one-row DataFrame from the input dict."""
    df = pd.DataFrame([features])
    preds = model.predict(df)
    value = preds[0]
    # Convert numpy scalar -> native Python so it serializes to JSON cleanly.
    return value.item() if hasattr(value, "item") else value
