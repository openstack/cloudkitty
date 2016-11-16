#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

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
