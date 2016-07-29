"""Rename mapping table to hashmap_mappings.

Revision ID: 10d2738b67df
Revises: 54cc17accf2c
Create Date: 2016-05-24 18:37:25.305430

"""

# revision identifiers, used by Alembic.
revision = '10d2738b67df'
down_revision = '54cc17accf2c'

from alembic import op


def upgrade():
    op.rename_table('hashmap_maps', 'hashmap_mappings')
