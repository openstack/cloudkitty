#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
from cloudkitty.api.v2 import utils as api_utils


def init(app):
    api_utils.do_init(app, 'task', [
        {
            'module': __name__ + '.' + 'reprocess',
            'resource_class': 'ReprocessSchedulerPostApi',
            'url': '/reprocesses',
        },
        {
            'module': __name__ + '.' + 'reprocess',
            'resource_class': 'ReprocessSchedulerGetApi',
            'url': '/reprocesses/<path_scope_id>',
        },
        {
            'module': __name__ + '.' + 'reprocess',
            'resource_class': 'ReprocessesSchedulerGetApi',
            'url': '/reprocesses',
        },
    ])
    return app
