from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8bdb18defe49'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('problems',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('time_limit', sa.Float(), nullable=False),
    sa.Column('points', sa.Float(), nullable=False),
    sa.Column('user_count', sa.Integer(), nullable=False),
    sa.Column('ac_rate', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('problem_authors',
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('problem_id', 'user_id')
    )
    op.create_table('problem_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('zipfile', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('problem_id')
    )
    op.create_table('submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('time', sa.Float(), nullable=True),
    sa.Column('points', sa.Float(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'COMPILING', 'RUNNING', 'ACCEPTED', 'WRONG_ANSWER', 'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED', 'RUNTIME_ERROR', 'COMPILE_ERROR', name='submissionstatus'), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('cycles', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_problem_scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('problem_id', sa.Integer(), nullable=False),
    sa.Column('max_score', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('problem_test_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('problem_data_id', sa.Integer(), nullable=False),
    sa.Column('input_file', sa.String(), nullable=False),
    sa.Column('output_file', sa.String(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['problem_data_id'], ['problem_data.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('problem_test_cases')
    op.drop_table('user_problem_scores')
    op.drop_table('submissions')
    op.drop_table('problem_data')
    op.drop_table('problem_authors')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.drop_table('problems')
