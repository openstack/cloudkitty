"""Clean hashmap fields constraints.

Revision ID: c88a06b1cfce
Revises: f8c799db4aa0
Create Date: 2016-05-19 18:06:43.315066

"""

# revision identifiers, used by Alembic.
revision = 'c88a06b1cfce'
down_revision = 'f8c799db4aa0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table(
        'hashmap_fields',
        # NOTE(sheeprine): Forced reflection is needed because of SQLAlchemy's
        # SQLite backend limitation reflecting ON DELETE clauses.
        reflect_args=[
            sa.Column(
                'service_id',
                sa.Integer,
                sa.ForeignKey(
                    'hashmap_services.id',
                    ondelete='CASCADE',
                    name='fk_hashmap_fields_service_id_hashmap_services'),
                nullable=False)]) as batch_op:
        batch_op.drop_constraint(
            u'uniq_field',
            type_='unique')
        batch_op.create_unique_constraint(
            'uniq_field_per_service',
            ['service_id', 'name'])
        batch_op.drop_constraint(
            'uniq_map_service_field',
            type_='unique')
