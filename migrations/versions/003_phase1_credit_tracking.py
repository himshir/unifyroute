"""Phase 1: USD credit tracking infrastructure

Revision ID: 003_phase1_credit
Revises: 002_phase0_correlation
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '003_phase1_credit'
down_revision = '002_phase0_correlation'
branch_labels = None
depends_on = None


def upgrade():
    # Create credit_balances table for USD-level balance per credential
    op.create_table(
        'credit_balances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('credential_id', sa.UUID(), nullable=False),
        sa.Column('usd_remaining', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('usd_granted', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('usd_used', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('polled_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['credential_id'], ['credentials.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credit_balances_cred_polled', 'credit_balances', ['credential_id', 'polled_at'])


def downgrade():
    op.drop_index('ix_credit_balances_cred_polled')
    op.drop_table('credit_balances')
