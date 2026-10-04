from alembic import op
import sqlalchemy as sa

revision = 'c28e905b7d12'
down_revision = 'b719a204f601'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('submissions', sa.Column('compile_output', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('submissions', 'compile_output')
