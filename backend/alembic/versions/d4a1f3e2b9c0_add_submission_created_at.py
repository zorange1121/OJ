from alembic import op
import sqlalchemy as sa

revision = 'd4a1f3e2b9c0'
down_revision = 'c28e905b7d12'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('submissions', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('submissions') as batch:
        batch.alter_column('created_at', server_default=sa.func.now(), existing_type=sa.DateTime(timezone=True))
    op.create_index('ix_submissions_created_at', 'submissions', ['created_at'])


def downgrade():
    op.drop_index('ix_submissions_created_at', table_name='submissions')
    op.drop_column('submissions', 'created_at')
