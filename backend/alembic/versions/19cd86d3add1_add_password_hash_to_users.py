from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '19cd86d3add1'
down_revision: Union[str, Sequence[str], None] = 'ad5ea9140aae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
