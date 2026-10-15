"""Add request_id to audit_jobs

Revision ID: 004_add_request_id
Revises: 003_add_evaluation_ownership
Create Date: 2026-09-23 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_add_request_id'
down_revision: Union[str, None] = '003_add_evaluation_ownership'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('audit_jobs', sa.Column('request_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_audit_jobs_request_id'), 'audit_jobs', ['request_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_audit_jobs_request_id'), table_name='audit_jobs')
    op.drop_column('audit_jobs', 'request_id')
