"""create schedule configuration entities

Revision ID: 0004_schedule_configuration
Revises: 0003_services
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_schedule_configuration"
down_revision: Union[str, None] = "0003_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "barbershop_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False, server_default="Barbearia"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Fortaleza"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("booking_window_days", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("min_cancellation_notice_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("no_show_grace_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("slot_granularity_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "business_hours",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_hours_weekday", "business_hours", ["weekday"])
    op.create_table(
        "special_dates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custom_open_time", sa.Time(), nullable=True),
        sa.Column("custom_close_time", sa.Time(), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )
    op.create_index("ix_special_dates_date", "special_dates", ["date"])
    op.create_table(
        "blocked_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blocked_slots_date", "blocked_slots", ["date"])


def downgrade() -> None:
    op.drop_index("ix_blocked_slots_date", table_name="blocked_slots")
    op.drop_table("blocked_slots")
    op.drop_index("ix_special_dates_date", table_name="special_dates")
    op.drop_table("special_dates")
    op.drop_index("ix_business_hours_weekday", table_name="business_hours")
    op.drop_table("business_hours")
    op.drop_table("barbershop_settings")
