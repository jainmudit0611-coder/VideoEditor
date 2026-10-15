"""Add Evaluation Ownership and Baseline Fields

Revision ID: 003_add_evaluation_ownership
Revises: 002_add_users_table
Create Date: 2026-09-23 20:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_evaluation_ownership'
down_revision: Union[str, None] = '002_add_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'evaluation_runs' not in tables:
        op.create_table(
            'evaluation_runs',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('run_name', sa.String(length=256), nullable=False),
            sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='evaluationrunstatus'), nullable=False),
            sa.Column('dataset_version', sa.String(length=32), nullable=False),
            sa.Column('dataset_type', sa.String(length=64), nullable=False),
            sa.Column('case_count', sa.Integer(), nullable=False),
            sa.Column('model_name', sa.String(length=64), nullable=False),
            sa.Column('model_provider', sa.String(length=64), nullable=False),
            sa.Column('prompt_version', sa.String(length=32), nullable=False),
            sa.Column('config_version', sa.String(length=32), nullable=False),
            sa.Column('evaluation_version', sa.String(length=32), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('metrics', sa.JSON(), nullable=True),
            sa.Column('summary', sa.JSON(), nullable=True),
            sa.Column('discrepancies', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.String(length=2048), nullable=True),
            sa.Column('created_by', sa.String(length=36), nullable=True),
            sa.Column('is_baseline', sa.Boolean(), server_default=sa.text('0'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_evaluation_runs_id'), 'evaluation_runs', ['id'], unique=False)
        op.create_index(op.f('ix_evaluation_runs_status'), 'evaluation_runs', ['status'], unique=False)
        op.create_index(op.f('ix_evaluation_runs_created_at'), 'evaluation_runs', ['created_at'], unique=False)
        op.create_index(op.f('ix_evaluation_runs_created_by'), 'evaluation_runs', ['created_by'], unique=False)
        op.create_index(op.f('ix_evaluation_runs_is_baseline'), 'evaluation_runs', ['is_baseline'], unique=False)
        op.create_index('idx_eval_run_status_created', 'evaluation_runs', ['status', 'created_at'], unique=False)
        op.create_index('idx_eval_run_dataset', 'evaluation_runs', ['dataset_version'], unique=False)
        op.create_index('idx_eval_run_owner_baseline', 'evaluation_runs', ['created_by', 'is_baseline'], unique=False)
    else:
        columns = [c['name'] for c in inspector.get_columns('evaluation_runs')]
        if 'created_by' not in columns:
            op.add_column('evaluation_runs', sa.Column('created_by', sa.String(length=36), nullable=True))
            op.create_index(op.f('ix_evaluation_runs_created_by'), 'evaluation_runs', ['created_by'], unique=False)
        if 'is_baseline' not in columns:
            op.add_column('evaluation_runs', sa.Column('is_baseline', sa.Boolean(), server_default=sa.text('0'), nullable=False))
            op.create_index(op.f('ix_evaluation_runs_is_baseline'), 'evaluation_runs', ['is_baseline'], unique=False)
        op.create_index('idx_eval_run_owner_baseline', 'evaluation_runs', ['created_by', 'is_baseline'], unique=False)

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if 'evaluation_runs' in tables:
        op.drop_table('evaluation_runs')
