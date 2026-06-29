"""
Trainer registry — maps a dataset modality to the Trainer that handles it.

The worker calls `get_trainer(dataset.modality)` and runs it; it never needs to
know whether the job is tabular, image, or text. Register new trainers here as
new modalities are added.
"""

from app.services.trainers.base import Trainer, TrainOutcome
from app.services.trainers.tabular import TabularTrainer

# modality -> trainer instance
_TRAINERS: dict[str, Trainer] = {t.modality: t for t in (TabularTrainer(),)}


def get_trainer(modality: str) -> Trainer:
    """Return the trainer for a dataset modality, or raise if unsupported."""
    trainer = _TRAINERS.get(modality)
    if trainer is None:
        raise ValueError(f"No trainer registered for modality {modality!r}")
    return trainer


__all__ = ["Trainer", "TrainOutcome", "get_trainer"]
