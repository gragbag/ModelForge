"""
Pydantic SCHEMAS for datasets.

NEW CONCEPT — schemas vs. models. You now have TWO representations of a dataset:

  * SQLAlchemy model (app/models/dataset.py)  -> the DATABASE shape (a table row)
  * Pydantic schema   (this file)             -> the API shape (the JSON in/out)

Why separate them? They serve different masters:
  - The model has DB concerns (indexes, foreign keys, internal columns).
  - The schema defines exactly what your API exposes to the outside world.

Keeping them apart means you can change your DB without breaking your API
contract, and you never accidentally leak an internal column to users. FastAPI
uses the schema to validate output and to generate the OpenAPI docs.

`from_attributes = True` lets Pydantic read straight from a SQLAlchemy object
(it reads attributes like `.id`, `.filename`), so you can return a DB model and
FastAPI converts it to this schema automatically.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetRead(BaseModel):
    """The shape of a dataset as returned by the API (response model)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    s3_key: str
    size_bytes: int
    row_count: int
    column_count: int
    modality: str
    created_at: datetime
