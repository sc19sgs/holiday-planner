from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import DateTime
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '7420e22cc56e'
down_revision = '1c8b853d20ec'
branch_labels = None
depends_on = None


def upgrade():
    # Add the column with a default value
    with op.batch_alter_table('trip') as batch_op:
        batch_op.add_column(sa.Column('start_date', sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # Update existing rows to have the default value
    trip_table = table('trip', column('start_date', DateTime))
    op.execute(trip_table.update().values(start_date=datetime.utcnow()))

    # Remove the server default if not needed anymore
    with op.batch_alter_table('trip') as batch_op:
        batch_op.alter_column('start_date', server_default=None)


def downgrade():
    with op.batch_alter_table('trip') as batch_op:
        batch_op.drop_column('start_date')
