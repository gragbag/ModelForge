"""add task_type to jobs

Revision ID: e8e10b4bf758
Revises: d26627cad16c
Create Date: 2026-06-15 21:58:45.575757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e8e10b4bf758'
down_revision: Union[str, Sequence[str], None] = 'd26627cad16c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The enum type. We create it explicitly because op.add_column does NOT
# auto-create a Postgres enum type (unlike create_table, which does).
tasktype = postgresql.ENUM('CLASSIFICATION', 'REGRESSION', name='tasktype')


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: create the enum TYPE in Postgres (checkfirst avoids errors if it
    # somehow already exists).
    tasktype.create(op.get_bind(), checkfirst=True)
    # Step 2: add the column using that type. create_type=False tells SQLAlchemy
    # not to try creating the type again (we just did it above).
    op.add_column(
        'jobs',
        sa.Column(
            'task_type',
            postgresql.ENUM('CLASSIFICATION', 'REGRESSION', name='tasktype', create_type=False),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order: drop the column first, then the type it depended on.
    op.drop_column('jobs', 'task_type')
    tasktype.drop(op.get_bind(), checkfirst=True)
