"""
The `deployments` table — one row per "deployed" model.

A deployment points at a specific REGISTERED model version in the MLflow Model
Registry. Creating a deployment makes a prediction endpoint available at
/deployments/{id}/predict, which loads that exact model version and serves it.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Which registered MLflow model + version this deployment serves.
    model_name: Mapped[str] = mapped_column(nullable=False)
    model_version: Mapped[str] = mapped_column(nullable=False)
    # The user who created the deployment (ownership, like datasets/jobs).
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Deployment id={self.id} {self.model_name} v{self.model_version}>"
