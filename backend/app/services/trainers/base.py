"""
The Trainer abstraction.

Each data modality (tabular, image, text) trains models in its own way — it
loads data differently, builds different kinds of models, serializes them
differently, and logs different things. A `Trainer` encapsulates that whole
modality-specific pipeline so the Celery worker stays modality-agnostic: it
just picks the right trainer for the dataset and records the result.

To add a new modality, implement `Trainer.run` and register it in __init__.py.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.dataset import Dataset
from app.models.job import Job

# Called by epoch-based trainers to report live progress, e.g.
# {"current_epoch": 3, "total_epochs": 10, "history": [{epoch, train_loss, val_accuracy}, ...]}.
ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class TrainOutcome:
    """What a finished training run hands back to the worker to store on the Job."""

    metrics: dict[str, float]
    model_s3_key: str  # where the serialized model was uploaded in S3


class Trainer(ABC):
    """A modality-specific training backend."""

    #: The dataset modality this trainer handles (see app.models.dataset).
    modality: str

    @abstractmethod
    def run(
        self, job: Job, dataset: Dataset, progress_cb: ProgressCallback | None = None
    ) -> TrainOutcome:
        """Load the dataset, train per the job's config, persist the model +
        log the run, and return what the worker should save on the Job.

        `progress_cb`, if given, is called by epoch-based trainers after each
        epoch to report live progress. Data/network errors should propagate —
        the worker classifies them for retry vs. permanent failure.
        """
        raise NotImplementedError
