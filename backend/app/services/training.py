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

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
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
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.models.job import TaskType

_RANDOM_STATE = 42


@dataclass
class Param:
    """One tunable hyperparameter the UI can render and the user can set."""

    name: str
    label: str
    type: str  # "int" | "float" | "select"
    default: Any
    options: list[str] | None = None  # only for type == "select"


@dataclass
class ModelSpec:
    """A model's two variants (built from a params dict) + its tunable params."""

    classifier: Callable[[dict[str, Any]], Any]
    regressor: Callable[[dict[str, Any]], Any]
    params: list[Param] = field(default_factory=list)


def _layers(value: Any) -> tuple[int, ...]:
    """Parse an MLP hidden-layer spec like '64,32' into a tuple (64, 32)."""
    return tuple(int(x) for x in str(value).split(","))


# Registry: model_type -> ModelSpec. Each factory takes a params dict `p` (with
# defaults already filled in). To support a new model, add a row here.
MODEL_REGISTRY: dict[str, ModelSpec] = {
    "random_forest": ModelSpec(
        classifier=lambda p: RandomForestClassifier(
            n_estimators=p["n_estimators"], max_depth=p["max_depth"] or None, random_state=_RANDOM_STATE
        ),
        regressor=lambda p: RandomForestRegressor(
            n_estimators=p["n_estimators"], max_depth=p["max_depth"] or None, random_state=_RANDOM_STATE
        ),
        params=[
            Param("n_estimators", "Trees", "int", 100),
            Param("max_depth", "Max depth (0 = unlimited)", "int", 0),
        ],
    ),
    "gradient_boosting": ModelSpec(
        classifier=lambda p: GradientBoostingClassifier(
            n_estimators=p["n_estimators"], learning_rate=p["learning_rate"], random_state=_RANDOM_STATE
        ),
        regressor=lambda p: GradientBoostingRegressor(
            n_estimators=p["n_estimators"], learning_rate=p["learning_rate"], random_state=_RANDOM_STATE
        ),
        params=[
            Param("n_estimators", "Trees", "int", 100),
            Param("learning_rate", "Learning rate", "float", 0.1),
        ],
    ),
    "decision_tree": ModelSpec(
        classifier=lambda p: DecisionTreeClassifier(
            max_depth=p["max_depth"] or None, random_state=_RANDOM_STATE
        ),
        regressor=lambda p: DecisionTreeRegressor(
            max_depth=p["max_depth"] or None, random_state=_RANDOM_STATE
        ),
        params=[Param("max_depth", "Max depth (0 = unlimited)", "int", 0)],
    ),
    "linear": ModelSpec(
        classifier=lambda p: LogisticRegression(max_iter=1000),
        regressor=lambda p: LinearRegression(),
        params=[],
    ),
    "svm": ModelSpec(
        classifier=lambda p: SVC(C=p["C"], kernel=p["kernel"], random_state=_RANDOM_STATE),
        regressor=lambda p: SVR(C=p["C"], kernel=p["kernel"]),
        params=[
            Param("C", "Regularization (C)", "float", 1.0),
            Param("kernel", "Kernel", "select", "rbf", options=["rbf", "linear", "poly"]),
        ],
    ),
    "knn": ModelSpec(
        classifier=lambda p: KNeighborsClassifier(n_neighbors=p["n_neighbors"]),
        regressor=lambda p: KNeighborsRegressor(n_neighbors=p["n_neighbors"]),
        params=[Param("n_neighbors", "Neighbors (k)", "int", 5)],
    ),
    "mlp": ModelSpec(
        classifier=lambda p: MLPClassifier(
            hidden_layer_sizes=_layers(p["hidden_layers"]), max_iter=p["max_iter"], random_state=_RANDOM_STATE
        ),
        regressor=lambda p: MLPRegressor(
            hidden_layer_sizes=_layers(p["hidden_layers"]), max_iter=p["max_iter"], random_state=_RANDOM_STATE
        ),
        params=[
            Param("hidden_layers", "Hidden layers", "select", "100", options=["100", "100,50", "64,32"]),
            Param("max_iter", "Max iterations", "int", 500),
        ],
    ),
}

# The valid model_type values (for validation).
MODEL_TYPES = list(MODEL_REGISTRY)


def model_specs() -> list[dict[str, Any]]:
    """Describe every model + its tunable params, for the UI to render dynamically."""
    return [
        {
            "name": name,
            "params": [
                {"name": p.name, "label": p.label, "type": p.type,
                 "default": p.default, "options": p.options}
                for p in spec.params
            ],
        }
        for name, spec in MODEL_REGISTRY.items()
    ]


def _coerce(param: Param, value: Any) -> Any:
    """Cast a user-supplied value to the param's type; fall back to default."""
    try:
        if param.type == "int":
            return int(value)
        if param.type == "float":
            return float(value)
    except (ValueError, TypeError):
        return param.default
    return value


def _build_model(
    task_type: TaskType, model_type: str, params: dict[str, Any] | None = None,
    scale_features: bool = False,
) -> Any:
    """Build the scikit-learn model for (task_type, model_type) with the given
    hyperparameters (defaults fill in any the user didn't set). If scale_features
    is set, wrap it in a StandardScaler pipeline (important for SVM, KNN, MLP)."""
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"Unsupported model_type: {model_type!r}")

    spec = MODEL_REGISTRY[model_type]
    provided = params or {}
    merged = {p.name: _coerce(p, provided.get(p.name, p.default)) for p in spec.params}

    factory = spec.classifier if task_type == TaskType.CLASSIFICATION else spec.regressor
    model = factory(merged)
    if scale_features:
        model = make_pipeline(StandardScaler(), model)
    return model


def train_and_evaluate(
    df: pd.DataFrame,
    target_column: str,
    task_type: TaskType,
    model_type: str,
    hyperparameters: dict[str, Any] | None = None,
    scale_features: bool = False,
) -> tuple[Any, dict[str, float]]:
    """
    Train a model and compute metrics. Returns (trained_model, metrics_dict).

    Raises ValueError if the target column isn't in the data — the worker turns
    that into a FAILED job with a clear error message.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column {target_column!r} not found in dataset")

    # Split into features (X = all columns except the target) and target (y).
    X = df.drop(columns=[target_column])
    y = df[target_column]

    # Train on 75%, evaluate on the held-out 25% (an honest measure of performance).
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = _build_model(task_type, model_type, hyperparameters, scale_features)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

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


def _regression_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    """Metrics for regression."""
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred))
    }
