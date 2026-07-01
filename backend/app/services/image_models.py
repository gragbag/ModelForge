"""
PyTorch architectures for image datasets (worker-only — imports torch).

The hyperparameter *specs* live in image_specs.py (torch-free) so the API can
read them without pulling in torch. The CNN is intentionally a small, fixed
shape with a couple of knobs — full architecture search is out of scope.
"""

from typing import Any

import torch
from torch import nn


class SimpleCNN(nn.Module):
    """Two conv→ReLU→maxpool blocks, then a linear classifier head."""

    def __init__(
        self,
        num_classes: int,
        img_size: int,
        base_channels: int = 16,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        c = base_channels
        self.features = nn.Sequential(
            nn.Conv2d(3, c, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(c, c * 2, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        # Two 2x pools -> spatial dim is img_size / 4.
        flat = (img_size // 4) ** 2 * c * 2
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(flat, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def build(
    model_type: str, num_classes: int, img_size: int, params: dict[str, Any]
) -> nn.Module:
    """Construct the model for an image model_type from its (merged) params."""
    if model_type == "cnn":
        return SimpleCNN(
            num_classes,
            img_size,
            base_channels=params["base_channels"],
            dropout=params["dropout"],
        )
    raise ValueError(f"Unknown image model_type: {model_type!r}")
