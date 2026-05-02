"""Add part_features table for STEP feature recognition

Revision ID: a3f1b2c4d5e6
Revises: 26088dd29943
Create Date: 2026-05-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3f1b2c4d5e6'
down_revision: Union[str, None] = '26088dd29943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'part_features',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feature_type', sa.String(50), nullable=False),
        sa.Column('class_index', sa.Integer(), nullable=False),
        sa.Column('center_x', sa.Float(), nullable=False),
        sa.Column('center_y', sa.Float(), nullable=False),
        sa.Column('center_z', sa.Float(), nullable=False),
        sa.Column('normal_x', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('normal_y', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('normal_z', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('radius', sa.Float(), nullable=True),
        sa.Column('depth', sa.Float(), nullable=True),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('length', sa.Float(), nullable=True),
        sa.Column('properties_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['project_id'], ['assembly_projects.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_part_features_project_id', 'part_features', ['project_id'])
    op.create_index('ix_part_features_feature_type', 'part_features', ['feature_type'])


def downgrade() -> None:
    op.drop_index('ix_part_features_feature_type', table_name='part_features')
    op.drop_index('ix_part_features_project_id', table_name='part_features')
    op.drop_table('part_features')
