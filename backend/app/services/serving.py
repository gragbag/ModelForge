"""
Model serving — load registered models from MLflow and run predictions.

Loading a model downloads its artifact, which is slow, so we CACHE loaded models
in memory keyed by (name, version). A second prediction for the same model reuses
the in-memory copy instead of re-downloading.
"""

import logging
from typing import Any

import mlflow
import pandas as pd
from mlflow import MlflowClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory cache: (model_name, model_version) -> loaded model.
_model_cache: dict[tuple[str, str], Any] = {}


def list_model_versions() -> list[dict[str, str]]:
    """Return EVERY registered model's versions from the MLflow registry (name +
    version), so the deploy UI can show meaningful names instead of bare numbers.
    Best-effort: returns [] if MLflow is unreachable."""
    try:
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        # search_model_versions() with no filter returns EVERY version across all
        # registered models. (search_registered_models() proved unreliable here.)
        out = [
            {
                "name": v.name,
                "version": v.version,
                "stage": v.current_stage,
                "status": v.status,
            }
            for v in client.search_model_versions()
        ]
        # Group by name, newest version first within each.
        out.sort(key=lambda x: (x["name"], -int(x["version"])))
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not list model versions: %s", exc)
        return []


def load_model(model_name: str, model_version: str) -> Any:
    """Load a registered model version from the MLflow Model Registry (cached)."""
    key = (model_name, model_version)
    if key not in _model_cache:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        # "models:/<name>/<version>" is MLflow's URI for a registered model version.
        _model_cache[key] = mlflow.pyfunc.load_model(f"models:/{model_name}/{model_version}")
    return _model_cache[key]


def predict_batch(model: Any, rows: list[dict[str, Any]]) -> list[Any]:
    """Run predictions for one or more rows. Builds a DataFrame from the rows
    (columns must match the model's training features) and returns one prediction
    per row, converted to native Python types so they serialize to JSON."""
    df = pd.DataFrame(rows)
    preds = model.predict(df)
    return [p.item() if hasattr(p, "item") else p for p in preds]
