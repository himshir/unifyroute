"""Phase 2: Rules engine (Brain v2) infrastructure

Revision ID: 004_phase2_rules
Revises: 003_phase1_credit
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '004_phase2_rules'
down_revision = '003_phase1_credit'
branch_labels = None
depends_on = None


def upgrade():
    # Create routing_rules table
    op.create_table(
        'routing_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('match', sa.JSON(), nullable=False),
        sa.Column('action', sa.JSON(), nullable=False),
        sa.Column('scope', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_routing_rules_name', 'routing_rules', ['name'])
    op.create_index('ix_routing_rules_enabled_priority', 'routing_rules', ['enabled', 'priority'])

    # Create rule_evaluations table
    op.create_table(
        'rule_evaluations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('matched', sa.Boolean(), nullable=False),
        sa.Column('action_applied', sa.JSON(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['request_id'], ['request_logs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['routing_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rule_evals_request_id', 'rule_evaluations', ['request_id'])


def downgrade():
    op.drop_index('ix_rule_evals_request_id')
    op.drop_table('rule_evaluations')
    op.drop_index('ix_routing_rules_enabled_priority')
    op.drop_index('ix_routing_rules_name')
    op.drop_table('routing_rules')
