"""
The actual machine learning — pure and isolated.

Design note: this module knows NOTHING about S3, the database, or Celery. It
just takes a pandas DataFrame and returns a trained model + metrics. Keeping the
ML logic pure like this makes it easy to test and reason about; the worker
(tasks.py) handles the "plumbing" (download, save, update DB) around it.

The scikit-learn pattern you'll use is always the same four beats:
    1. split data into X (features) and y (target)
    2. split into train/test sets
    3. model.fit(X_train, y_train)        # learn
    4. model.predict(X_test)              # evaluate on unseen data
"""

from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from app.models.job import TaskType


def _build_model(task_type: TaskType, model_type: str) -> Any:
    """
    Pick the scikit-learn model. For now we only support 'random_forest', which
    has both a classifier and a regressor variant. Built for you — this is the
    lookup that maps (task_type, model_type) -> a model object.
    """
    if model_type != "random_forest":
        raise ValueError(f"Unsupported model_type: {model_type!r}")

    if task_type == TaskType.CLASSIFICATION:
        return RandomForestClassifier(n_estimators=100, random_state=42)
    else:  # REGRESSION
        return RandomForestRegressor(n_estimators=100, random_state=42)


def train_and_evaluate(
    df: pd.DataFrame,
    target_column: str,
    task_type: TaskType,
    model_type: str,
) -> tuple[Any, dict[str, float]]:
    """
    Train a model and compute metrics. Returns (trained_model, metrics_dict).

    Raises ValueError if the target column isn't in the data — the worker turns
    that into a FAILED job with a clear error message.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column {target_column!r} not found in dataset")

    # --- 1. Split into features (X) and target (y) -- worked example --------
    # X = everything EXCEPT the target column; y = the target column.
    X = df.drop(columns=[target_column])
    y = df[target_column]

    # --- 2. Train/test split -- worked example ------------------------------
    # We train on 75% and evaluate on the held-out 25% (data the model didn't
    # see), which is how you get an honest measure of performance.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    # --- 3. Build the model -- worked example -------------------------------
    model = _build_model(task_type, model_type)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    # ------------------------------------------------------------------
    # TODO(you): the heart of scikit-learn — train, then predict.
    #
    # 1) Train the model on the training data:
    #        model.fit(X_train, y_train)
    #
    # 2) Predict on the held-out test data:
    #        predictions = model.predict(X_test)
    #
    # Write those two lines below.
    # ------------------------------------------------------------------

    # --- 4. Compute task-appropriate metrics --------------------------------
    # (This runs once you've created `predictions` above.)
    if task_type == TaskType.CLASSIFICATION:
        metrics = _classification_metrics(y_test, predictions)
    else:
        metrics = _regression_metrics(y_test, predictions)

    return model, metrics


def _classification_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    """Metrics for classification. `zero_division=0` avoids warnings on tiny
    datasets where a class may be missing from the test split."""

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
    }
    # ------------------------------------------------------------------
    # TODO(you): build and return a dict of classification metrics.
    # Use these sklearn functions (already imported), all take (y_true, y_pred):
    #   accuracy_score(y_true, y_pred)
    #   precision_score(y_true, y_pred, average="weighted", zero_division=0)
    #   recall_score(y_true, y_pred, average="weighted", zero_division=0)
    #   f1_score(y_true, y_pred, average="weighted", zero_division=0)
    #
    # Return e.g.:
    #   return {
    #       "accuracy": float(accuracy_score(y_true, y_pred)),
    #       "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
    #       "recall": ...,
    #       "f1": ...,
    #   }
    # ------------------------------------------------------------------
    # raise NotImplementedError("TODO(you): return classification metrics dict")


def _regression_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    """Metrics for regression."""
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred))
    }

    # ------------------------------------------------------------------
    # TODO(you): build and return a dict of regression metrics.
    # Use (already imported):
    #   mean_squared_error(y_true, y_pred)   -> square-root it for RMSE
    #   mean_absolute_error(y_true, y_pred)
    #   r2_score(y_true, y_pred)
    #
    # Return e.g.:
    #   rmse = float(mean_squared_error(y_true, y_pred)) ** 0.5
    #   return {"rmse": rmse, "mae": float(mean_absolute_error(y_true, y_pred)),
    #           "r2": float(r2_score(y_true, y_pred))}
    # ------------------------------------------------------------------
    # raise NotImplementedError("TODO(you): return regression metrics dict")
