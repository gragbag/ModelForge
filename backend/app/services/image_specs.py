"""
Hyperparameter specs for image models — deliberately torch-free so the API can
import it (validation + the model-types endpoint). The actual PyTorch
architectures live in image_models.py, which is only imported in the worker.

The spec dicts mirror the tabular model_specs() shape, so the same UI renders them.
"""

from typing import Any

IMAGE_MODEL_PARAMS: dict[str, list[dict[str, Any]]] = {
    "cnn": [
        {"name": "epochs", "label": "Epochs", "type": "int", "default": 5, "options": None},
        {"name": "batch_size", "label": "Batch size", "type": "int", "default": 32, "options": None},
        {"name": "learning_rate", "label": "Learning rate", "type": "float", "default": 0.001, "options": None},
        {"name": "img_size", "label": "Image size", "type": "select", "default": "32", "options": ["32", "64"]},
        {"name": "base_channels", "label": "Conv channels", "type": "int", "default": 16, "options": None},
        {"name": "dropout", "label": "Dropout", "type": "float", "default": 0.0, "options": None},
    ],
}

IMAGE_MODEL_TYPES = list(IMAGE_MODEL_PARAMS)


def image_model_specs() -> list[dict[str, Any]]:
    """UI specs for image models (same shape as the tabular model_specs())."""
    return [{"name": name, "params": params} for name, params in IMAGE_MODEL_PARAMS.items()]


def _coerce(spec: dict[str, Any], value: Any) -> Any:
    try:
        if spec["type"] == "int":
            return int(value)
        if spec["type"] == "float":
            return float(value)
    except (ValueError, TypeError):
        return spec["default"]
    return value


def merged_params(model_type: str, provided: dict[str, Any] | None) -> dict[str, Any]:
    """Fill defaults + type-coerce a job's hyperparameters for an image model."""
    provided = provided or {}
    return {
        s["name"]: _coerce(s, provided.get(s["name"], s["default"]))
        for s in IMAGE_MODEL_PARAMS[model_type]
    }
