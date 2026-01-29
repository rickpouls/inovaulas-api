"""add class_code and course_name to timetable_entries

Revision ID: 2dddff6dd067
Revises: cf552a4b4e70
Create Date: 2026-01-29 21:10:23.776999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2dddff6dd067'
down_revision: Union[str, Sequence[str], None] = 'cf552a4b4e70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("timetable_entries", sa.Column("class_code", sa.String(length=20), nullable=True))
    op.add_column("timetable_entries", sa.Column("course_name", sa.String(length=60), nullable=True))

    op.create_index("ix_timetable_entries_class_code", "timetable_entries", ["class_code"])
    op.create_index("ix_timetable_entries_course_name", "timetable_entries", ["course_name"])


def downgrade() -> None:
    op.drop_index("ix_timetable_entries_course_name", table_name="timetable_entries")
    op.drop_index("ix_timetable_entries_class_code", table_name="timetable_entries")

    op.drop_column("timetable_entries", "course_name")
    op.drop_column("timetable_entries", "class_code")
