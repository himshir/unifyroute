"""Phase 4: Enterprise logging and alerting

Revision ID: 006_phase4_alerts
Revises: 005_phase3_chat
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '006_phase4_alerts'
down_revision = '005_phase3_chat'
branch_labels = None
depends_on = None


def upgrade():
    # Create alerts table for monitoring and alerting
    op.create_table(
        'alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('condition', sa.JSON(), nullable=False),
        sa.Column('sinks', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_alerts_name', 'alerts', ['name'])
    op.create_index('ix_alerts_enabled', 'alerts', ['enabled'])


def downgrade():
    op.drop_index('ix_alerts_enabled')
    op.drop_index('ix_alerts_name')
    op.drop_table('alerts')
