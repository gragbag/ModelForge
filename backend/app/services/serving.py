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


def delete_model_version(model_name: str, model_version: str) -> None:
    """Delete a registered model version from the MLflow registry (and the whole
    registered model if that was its last version). Evicts any cached copies."""
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    client.delete_model_version(model_name, model_version)

    # If no versions remain, remove the now-empty registered model too (tidy-up).
    try:
        if not client.search_model_versions(f"name='{model_name}'"):
            client.delete_registered_model(model_name)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("Could not remove empty model %s: %s", model_name, exc)

    # Drop any cached loaded model / params for this version.
    key = (model_name, model_version)
    _model_cache.pop(key, None)
    _torch_cache.pop(key, None)
    _run_params_cache.pop(key, None)


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


# --- Image serving --------------------------------------------------------
# Torch is imported lazily inside these functions so the module (and the API
# process) stays torch-free until an image prediction actually runs.

_torch_cache: dict[tuple[str, str], Any] = {}
_run_params_cache: dict[tuple[str, str], dict[str, str]] = {}


def run_params(model_name: str, model_version: str) -> dict[str, str]:
    """The MLflow params logged for a model version's run (cached). Used to read
    image metadata (modality, classes, img_size) recorded at training time."""
    key = (model_name, model_version)
    if key not in _run_params_cache:
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        mv = client.get_model_version(model_name, model_version)
        _run_params_cache[key] = (
            client.get_run(mv.run_id).data.params if mv.run_id else {}
        )
    return _run_params_cache[key]


def is_image_model(model_name: str, model_version: str) -> bool:
    """True if this registered model was trained on image data."""
    return run_params(model_name, model_version).get("modality") == "image"


def _load_torch(model_name: str, model_version: str) -> Any:
    """Load + cache a registered PyTorch model from the MLflow registry."""
    key = (model_name, model_version)
    if key not in _torch_cache:
        from mlflow import pytorch as mlflow_pytorch  # lazy (pulls in torch)

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        _torch_cache[key] = mlflow_pytorch.load_model(
            f"models:/{model_name}/{model_version}"
        )
    return _torch_cache[key]


def predict_images(
    model_name: str, model_version: str, images: list[bytes]
) -> list[dict[str, Any]]:
    """Classify raw image bytes. Resizes/normalizes each image with the same
    img_size used in training, runs the model, and maps outputs to class names."""
    import io as _io

    import torch
    from PIL import Image
    from torchvision import transforms

    params = run_params(model_name, model_version)
    classes = params.get("classes", "").split(",")
    img_size = int(params.get("img_size", "32"))

    model = _load_torch(model_name, model_version)
    model.eval()
    tfm = transforms.Compose(
        [transforms.Resize((img_size, img_size)), transforms.ToTensor()]
    )
    batch = torch.stack(
        [tfm(Image.open(_io.BytesIO(b)).convert("RGB")) for b in images]
    )
    with torch.no_grad():
        probs = torch.softmax(model(batch), dim=1)
        confidences, indices = probs.max(dim=1)

    results = []
    for i in range(len(images)):
        idx = int(indices[i])
        label = classes[idx] if idx < len(classes) else str(idx)
        results.append(
            {"prediction": label, "confidence": round(float(confidences[i]), 4)}
        )
    return results
