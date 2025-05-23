"""Remove MEGA cloud provider

Revision ID: 7c663f5ec8a1
Revises: 249b95f63f76
Create Date: 2025-05-13 11:29:12.009530+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c663f5ec8a1'
down_revision = '249b95f63f76'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("""
        DELETE FROM tasks_cloudsync WHERE credential_id IN (
            SELECT id FROM system_cloudcredentials WHERE provider = 'MEGA'
        )
    """)
    op.execute("DELETE FROM system_cloudcredentials WHERE provider = 'MEGA'")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass

    # ### end Alembic commands ###
