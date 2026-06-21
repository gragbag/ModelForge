"""
MLflow experiment tracking + model registry.

The worker calls `log_run(...)` after training to record the run in MLflow:
params, metrics, the trained model, and to register the model (versioned).

This is best-effort: if MLflow is unreachable, we log a warning but DON'T fail
the training job — tracking is secondary to actually producing the model.
"""

import logging

import mlflow
import mlflow.sklearn

from app.core.config import settings
from app.models.job import Job

logger = logging.getLogger(__name__)

# All runs go under one named experiment in the MLflow UI.
EXPERIMENT_NAME = "modelforge"
# The name models are registered under in the MLflow Model Registry.
REGISTERED_MODEL_NAME = "modelforge-model"


def log_run(job: Job, model, metrics: dict[str, float]) -> None:
    """Log one training run to MLflow and register the resulting model."""
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(EXPERIMENT_NAME)

        with mlflow.start_run(run_name=f"job-{job.id}"):
            mlflow.log_param("model_type", job.model_type)
            mlflow.log_param("target_column", job.target_column)
            mlflow.log_param("task_type", job.task_type.value)

            for name, value in metrics.items():
                mlflow.log_metric(name, value)
            
            # Register under the user-given model name (falls back to the default
            # for older jobs that have no name). Same name on a retrain -> new version.
            mlflow.sklearn.log_model(
                model, "model",
                registered_model_name=job.name or REGISTERED_MODEL_NAME,
            )

    except Exception as exc:  # noqa: BLE001 — tracking must never break training
        logger.warning("MLflow logging failed for job %s: %s", job.id, exc)
