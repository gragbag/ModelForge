"""
Trainer registry — maps a dataset modality to the Trainer that handles it.

The worker calls `get_trainer(dataset.modality)` and runs it; it never needs to
know whether the job is tabular or image. Trainers are imported LAZILY here so
that the heavy image trainer (which pulls in torch) only loads in the worker
when an image job actually runs — the API process never imports torch.
"""

from app.models.dataset import MODALITY_IMAGE, MODALITY_TABULAR
from app.services.trainers.base import Trainer, TrainOutcome


def get_trainer(modality: str) -> Trainer:
    """Return the trainer for a dataset modality, or raise if unsupported."""
    if modality == MODALITY_TABULAR:
        from app.services.trainers.tabular import TabularTrainer

        return TabularTrainer()
    if modality == MODALITY_IMAGE:
        from app.services.trainers.image import ImageTrainer

        return ImageTrainer()
    raise ValueError(f"No trainer registered for modality {modality!r}")


__all__ = ["Trainer", "TrainOutcome", "get_trainer"]
