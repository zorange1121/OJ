from alembic import op
import sqlalchemy as sa

revision = "b719a204f601"
down_revision = "19cd86d3add1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("submissions", sa.Column("lease_until", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("submissions", "lease_until")
