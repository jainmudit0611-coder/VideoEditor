"""Initial Audit Jobs Schema

Revision ID: 001_initial_audit_jobs
Revises: 
Create Date: 2026-09-22 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_audit_jobs'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'audit_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'PROCESSING', 'VERIFYING', 'COMPLETED', 'FAILED', 'CANCELLED', name='auditstatus'), nullable=False),
        sa.Column('video_url', sa.String(length=2048), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('current_stage', sa.String(length=64), nullable=False),
        sa.Column('iteration_count', sa.Integer(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=256), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.String(length=2048), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('timing_metrics', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_jobs_id'), 'audit_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_jobs_status'), 'audit_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_audit_jobs_created_at'), 'audit_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_jobs_idempotency_key'), 'audit_jobs', ['idempotency_key'], unique=False)
    op.create_index('idx_audit_status_created', 'audit_jobs', ['status', 'created_at'], unique=False)

def downgrade() -> None:
    op.drop_index('idx_audit_status_created', table_name='audit_jobs')
    op.drop_index(op.f('ix_audit_jobs_idempotency_key'), table_name='audit_jobs')
    op.drop_index(op.f('ix_audit_jobs_created_at'), table_name='audit_jobs')
    op.drop_index(op.f('ix_audit_jobs_status'), table_name='audit_jobs')
    op.drop_index(op.f('ix_audit_jobs_id'), table_name='audit_jobs')
    op.drop_table('audit_jobs')
