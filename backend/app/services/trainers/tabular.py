"""
Tabular trainer — the original scikit-learn pipeline, now behind the Trainer
interface. Reads the dataset CSV, trains via app.services.training, logs the run
to MLflow, and uploads the joblib-pickled model to S3.
"""

import io

import joblib
import pandas as pd

from app.core.config import settings
from app.models.dataset import Dataset, MODALITY_TABULAR
from app.models.job import Job
from app.services import storage, tracking, training
from app.services.trainers.base import Trainer, TrainOutcome


class TabularTrainer(Trainer):
    modality = MODALITY_TABULAR

    def run(self, job: Job, dataset: Dataset) -> TrainOutcome:
        if job.target_column is None:
            raise ValueError("Tabular training requires a target_column")

        # Load the CSV from object storage into a DataFrame.
        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
        df = pd.read_csv(io.BytesIO(raw))

        model, metrics = training.train_and_evaluate(
            df=df,
            target_column=job.target_column,
            task_type=job.task_type,
            model_type=job.model_type,
            hyperparameters=job.hyperparameters,
            scale_features=job.scale_features,
        )

        # Log to MLflow (params, metrics, model + registry). Best-effort:
        # tracking.log_run swallows its own errors so it can't fail the job.
        tracking.log_run(job, model, metrics)

        # Deterministic key: a re-run overwrites the SAME S3 object rather than
        # creating duplicates (idempotency).
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        model_key = f"models/{job.id}/model.joblib"
        storage.upload_fileobj(buffer.getvalue(), settings.s3_bucket_models, model_key)

        return TrainOutcome(metrics=metrics, model_s3_key=model_key)
