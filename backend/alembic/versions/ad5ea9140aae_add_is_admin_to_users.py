from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ad5ea9140aae'
down_revision: Union[str, Sequence[str], None] = '8bdb18defe49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('users', 'is_admin')
