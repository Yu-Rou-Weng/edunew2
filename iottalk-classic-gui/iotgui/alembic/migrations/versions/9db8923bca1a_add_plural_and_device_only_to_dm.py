"""add plural and device_only to DM

Revision ID: 9db8923bca1a
Revises: b3236c44c0b0
Create Date: 2020-05-19 15:45:42.098077

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9db8923bca1a'
down_revision = 'b3236c44c0b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Note: Sqlite3 is not support add non-null column
    op.add_column('DeviceModel', sa.Column('device_only', sa.Boolean(), nullable=True))
    op.execute("UPDATE DeviceModel SET device_only = false")
    op.add_column('DeviceModel', sa.Column('plural', sa.Boolean(), nullable=True))
    op.execute("UPDATE DeviceModel SET plural = false")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('DeviceModel', 'plural')
    op.drop_column('DeviceModel', 'device_only')
    # ### end Alembic commands ###
