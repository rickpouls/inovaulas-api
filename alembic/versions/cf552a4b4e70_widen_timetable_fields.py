"""widen timetable fields

Revision ID: cf552a4b4e70
Revises: eb3384e83892
Create Date: 2026-01-28 11:16:17.692944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cf552a4b4e70'
down_revision: Union[str, Sequence[str], None] = 'eb3384e83892'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("""
    ALTER TABLE timetable_entries
      ALTER COLUMN slot TYPE varchar(20)
      USING slot::text;
    """)

    op.execute("""
    ALTER TABLE timetable_entries
      ALTER COLUMN group_code TYPE varchar(200);
    """)

    op.execute("""
    ALTER TABLE timetable_entries
      ALTER COLUMN subject_code TYPE varchar(120);
    """)

def downgrade() -> None:
    """Downgrade schema."""
    pass
