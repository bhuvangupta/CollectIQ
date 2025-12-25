"""add_campaign_retry_fields

Revision ID: 30c30a07668b
Revises: a3f8c91d2e4b
Create Date: 2025-12-27 00:00:05.225779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30c30a07668b'
down_revision: Union[str, None] = 'a3f8c91d2e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add fields to campaigns table
    op.add_column('campaigns',
        sa.Column('telephony_provider', sa.String(50), nullable=True,
                  comment='Provider for calls: bolna, exotel, mock'))
    op.add_column('campaigns',
        sa.Column('retry_delays_minutes', sa.JSON(), nullable=True,
                  server_default='[30, 120, 480]',
                  comment='Retry delays in minutes after failed attempts'))

    # Add fields to campaign_borrowers table
    op.add_column('campaign_borrowers',
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True,
                  comment='Scheduled time for next retry attempt'))
    op.add_column('campaign_borrowers',
        sa.Column('last_attempt_outcome', sa.String(100), nullable=True,
                  comment='Outcome of last attempt: no_answer, busy, failed, etc.'))

    # Create index for efficient retry scheduling
    op.create_index(
        'ix_campaign_borrowers_retry',
        'campaign_borrowers',
        ['next_attempt_at', 'status'],
        postgresql_where=sa.text("status = 'retry_scheduled'")
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_campaign_borrowers_retry', table_name='campaign_borrowers')

    # Drop columns from campaign_borrowers
    op.drop_column('campaign_borrowers', 'last_attempt_outcome')
    op.drop_column('campaign_borrowers', 'next_attempt_at')

    # Drop columns from campaigns
    op.drop_column('campaigns', 'retry_delays_minutes')
    op.drop_column('campaigns', 'telephony_provider')
