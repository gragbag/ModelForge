"""
Importing the models here ensures SQLAlchemy (and Alembic) "sees" every table
when it inspects Base.metadata. If a model isn't imported anywhere, migrations
won't know about it. So we re-export them from one place.
"""

from app.models.dataset import Dataset
from app.models.job import Job

__all__ = ["Dataset", "Job"]
