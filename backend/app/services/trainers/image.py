"""
Image trainer (Phase 2) — trains a CNN on a folder-per-class image dataset.

Pipeline: download the dataset zip from object storage -> safely extract it ->
build a torchvision ImageFolder + DataLoader (resize/normalize) -> train the
chosen architecture -> evaluate -> log to MLflow -> upload the model to S3.

Only imported in the worker (via get_trainer), so torch stays out of the API.
"""

import io
import os
import tempfile
import zipfile

import torch
from torch import nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

from app.core.config import settings
from app.models.dataset import MODALITY_IMAGE, Dataset
from app.models.job import Job
from app.services import image_models, image_specs, storage, tracking
from app.services.trainers.base import Trainer, TrainOutcome

_SEED = 42


def _safe_extract(raw_bytes: bytes, dest: str) -> None:
    """Extract a zip to dest, rejecting path-traversal (zip-slip) entries."""
    dest_root = os.path.realpath(dest)
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        for member in zf.namelist():
            target = os.path.realpath(os.path.join(dest, member))
            if target != dest_root and not target.startswith(dest_root + os.sep):
                raise ValueError(f"Unsafe path in zip: {member!r}")
        zf.extractall(dest)


def _evaluate(model: nn.Module, loader: DataLoader, loss_fn: nn.Module) -> dict[str, float]:
    """Accuracy + average loss on a held-out loader."""
    model.eval()
    correct = total = 0
    loss_sum = 0.0
    with torch.no_grad():
        for xb, yb in loader:
            out = model(xb)
            loss_sum += float(loss_fn(out, yb)) * len(yb)
            correct += int((out.argmax(1) == yb).sum())
            total += len(yb)
    if not total:
        return {"accuracy": 0.0, "val_loss": 0.0}
    return {"accuracy": correct / total, "val_loss": loss_sum / total}


class ImageTrainer(Trainer):
    modality = MODALITY_IMAGE

    def run(self, job: Job, dataset: Dataset) -> TrainOutcome:
        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
        params = image_specs.merged_params(job.model_type, job.hyperparameters)
        img_size = int(params["img_size"])

        with tempfile.TemporaryDirectory() as tmp:
            _safe_extract(raw, tmp)

            tfm = transforms.Compose(
                [transforms.Resize((img_size, img_size)), transforms.ToTensor()]
            )
            ds = datasets.ImageFolder(tmp, transform=tfm)
            num_classes = len(ds.classes)

            # 80/20 train/val split (deterministic).
            n_val = max(1, int(len(ds) * 0.2))
            n_train = len(ds) - n_val
            gen = torch.Generator().manual_seed(_SEED)
            train_ds, val_ds = random_split(ds, [n_train, n_val], generator=gen)
            batch_size = params["batch_size"]
            train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
            val_dl = DataLoader(val_ds, batch_size=batch_size)

            torch.manual_seed(_SEED)
            model = image_models.build(job.model_type, num_classes, img_size, params)
            optimizer = torch.optim.Adam(model.parameters(), lr=params["learning_rate"])
            loss_fn = nn.CrossEntropyLoss()

            for _epoch in range(params["epochs"]):
                model.train()
                for xb, yb in train_dl:
                    optimizer.zero_grad()
                    loss = loss_fn(model(xb), yb)
                    loss.backward()
                    optimizer.step()

            metrics = _evaluate(model, val_dl, loss_fn)

            # Track the run in MLflow (pytorch flavor); record the classes + image
            # size so serving can preprocess + label predictions. Best-effort.
            tracking.log_run(
                job,
                model,
                metrics,
                flavor="pytorch",
                extra_params={
                    "modality": MODALITY_IMAGE,
                    "classes": ",".join(ds.classes),
                    "img_size": str(img_size),
                },
            )

            # Save the model + everything serving needs to rebuild + predict.
            model_key = f"models/{job.id}/model.pt"
            buffer = io.BytesIO()
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "model_type": job.model_type,
                    "params": params,
                    "img_size": img_size,
                    "classes": ds.classes,
                },
                buffer,
            )
            storage.upload_fileobj(
                buffer.getvalue(), settings.s3_bucket_models, model_key
            )

        return TrainOutcome(metrics=metrics, model_s3_key=model_key)
