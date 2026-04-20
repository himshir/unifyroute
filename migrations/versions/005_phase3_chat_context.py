"""Phase 3: Chat history with server-side context management

Revision ID: 005_phase3_chat
Revises: 004_phase2_rules
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '005_phase3_chat'
down_revision = '004_phase2_rules'
branch_labels = None
depends_on = None


def upgrade():
    # Create conversation_summaries table for rolling context summaries
    op.create_table(
        'conversation_summaries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('up_to_message_id', sa.UUID(), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['up_to_message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_summaries_session', 'conversation_summaries', ['session_id'])


def downgrade():
    op.drop_index('ix_conversation_summaries_session')
    op.drop_table('conversation_summaries')
