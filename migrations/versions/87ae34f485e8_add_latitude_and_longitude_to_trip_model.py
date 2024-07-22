from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '87ae34f485e8'
down_revision = '7420e22cc56e'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('trip') as batch_op:
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=False, server_default='0'))

def downgrade():
    with op.batch_alter_table('trip') as batch_op:
        batch_op.drop_column('latitude')
        batch_op.drop_column('longitude')
