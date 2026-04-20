"""Phase 5: Per-key budgets and credential management improvements

Revision ID: 007_phase5_budgets
Revises: 006_phase4_alerts
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '007_phase5_budgets'
down_revision = '006_phase4_alerts'
branch_labels = None
depends_on = None


def upgrade():
    # Create key_budgets table for per-gateway-key spend limits
    op.create_table(
        'key_budgets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key_id', sa.UUID(), nullable=False),
        sa.Column('window', sa.String(), nullable=False),
        sa.Column('limit_usd', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('spent_usd', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0'),
        sa.Column('resets_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_on_exceed', sa.String(), nullable=False, server_default='block'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['key_id'], ['gateway_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_key_budgets_key_id', 'key_budgets', ['key_id'])
    op.create_index('ix_key_budgets_enabled', 'key_budgets', ['enabled'])


def downgrade():
    op.drop_index('ix_key_budgets_enabled')
    op.drop_index('ix_key_budgets_key_id')
    op.drop_table('key_budgets')
