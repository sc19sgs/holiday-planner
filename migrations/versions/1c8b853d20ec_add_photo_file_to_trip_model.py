from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c8b853d20ec'
down_revision = '18e5eca42bbd'
branch_labels = None
depends_on = None


def upgrade():
    # Create a new table with the photo_file column
    op.create_table(
        'trip_new',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('date_posted', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('destination', sa.String(100), nullable=False),
        sa.Column('photo_file', sa.String(20), nullable=False, default='default.jpg'),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    )

    # Copy data from the old table to the new table
    op.execute('''
        INSERT INTO trip_new (id, name, date_posted, destination, user_id)
        SELECT id, name, date_posted, destination, user_id FROM trip
    ''')

    # Drop the old table
    op.drop_table('trip')

    # Rename the new table to the old table's name
    op.rename_table('trip_new', 'trip')


def downgrade():
    op.create_table(
        'trip_old',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('date_posted', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('destination', sa.String(100), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    )

    op.execute('''
        INSERT INTO trip_old (id, name, date_posted, destination, user_id)
        SELECT id, name, date_posted, destination, user_id FROM trip
    ''')

    op.drop_table('trip')
    op.rename_table('trip_old', 'trip')
