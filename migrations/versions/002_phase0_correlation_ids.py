"""Phase 0: Add request_id correlation ID infrastructure

Revision ID: 002_phase0_correlation
Revises: e462297b3a9e
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_phase0_correlation'
down_revision = 'e462297b3a9e'
branch_labels = None
depends_on = None


def upgrade():
    # Add request_id to request_logs (both as FK-like correlation ID and for efficiency)
    op.add_column('request_logs', sa.Column('request_id', sa.UUID(), nullable=False, server_default=sa.func.gen_random_uuid()))
    op.create_index('ix_request_logs_request_id', 'request_logs', ['request_id'])

    # Add request_id to system_events as FK to request_logs
    op.add_column('system_events', sa.Column('request_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_system_events_request_id', 'system_events', 'request_logs', ['request_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_system_events_request_id', 'system_events', ['request_id'])

    # Prepare for Phase 3: Add columns to chat_sessions for session scoping
    op.add_column('chat_sessions', sa.Column('client_key_id', sa.UUID(), nullable=True))
    op.add_column('chat_sessions', sa.Column('external_session_key', sa.String(), nullable=True))
    op.add_column('chat_sessions', sa.Column('metadata', sa.JSON(), server_default='{}'))
    op.create_foreign_key('fk_chat_sessions_client_key_id', 'chat_sessions', 'gateway_keys', ['client_key_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_chat_sessions_client_key_id', 'chat_sessions', ['client_key_id'])
    op.create_index('ix_chat_sessions_external_session_key', 'chat_sessions', ['external_session_key'], unique=True)

    # Prepare for Phase 3: Add columns to chat_messages
    op.add_column('chat_messages', sa.Column('request_id', sa.UUID(), nullable=True))
    op.add_column('chat_messages', sa.Column('tokens', sa.Integer(), nullable=True))
    op.add_column('chat_messages', sa.Column('redacted', sa.Boolean(), server_default='false'))
    op.create_foreign_key('fk_chat_messages_request_id', 'chat_messages', 'request_logs', ['request_id'], ['id'], ondelete='SET NULL')

    # Prepare for Phase 2 & 5: Add tags to gateway_keys and deleted_at to credentials
    op.add_column('gateway_keys', sa.Column('tags', sa.JSON(), server_default='[]'))
    op.add_column('credentials', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_credentials_deleted_at', 'credentials', ['deleted_at'])


def downgrade():
    op.drop_index('ix_credentials_deleted_at')
    op.drop_column('credentials', 'deleted_at')
    op.drop_column('gateway_keys', 'tags')

    op.drop_constraint('fk_chat_messages_request_id', 'chat_messages', type_='foreignkey')
    op.drop_column('chat_messages', 'redacted')
    op.drop_column('chat_messages', 'tokens')
    op.drop_column('chat_messages', 'request_id')

    op.drop_index('ix_chat_sessions_external_session_key')
    op.drop_index('ix_chat_sessions_client_key_id')
    op.drop_constraint('fk_chat_sessions_client_key_id', 'chat_sessions', type_='foreignkey')
    op.drop_column('chat_sessions', 'metadata')
    op.drop_column('chat_sessions', 'external_session_key')
    op.drop_column('chat_sessions', 'client_key_id')

    op.drop_index('ix_system_events_request_id')
    op.drop_constraint('fk_system_events_request_id', 'system_events', type_='foreignkey')
    op.drop_column('system_events', 'request_id')

    op.drop_index('ix_request_logs_request_id')
    op.drop_column('request_logs', 'request_id')
