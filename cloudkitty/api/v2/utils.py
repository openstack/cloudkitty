# Copyright 2018 Objectif Libre
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
import importlib
import itertools

import flask
import flask_restful
import voluptuous
from werkzeug import exceptions

from cloudkitty.api import v2 as v2_api
from cloudkitty.utils import json


class SingleQueryParam(object):
    """Voluptuous validator allowing to validate unique query parameters.

    This validator checks that a URL query parameter is provided only once,
    verifies its type and returns it directly, instead of returning a list
    containing a single element.

    Note that this validator uses ``voluptuous.Coerce`` internally and thus
    should not be used together with
    ``cloudkitty.utils.validation.get_string_type`` in python2.

    :param param_type: Type of the query parameter
    """
    def __init__(self, param_type):
        self._validate = voluptuous.Coerce(param_type)

    def __call__(self, v):
        if not isinstance(v, list):
            v = [v]
        if len(v) != 1:
            raise voluptuous.LengthInvalid('length of value must be 1')
        output = v[0]
        return self._validate(output)


class MultiQueryParam(object):
    """Voluptuous validator allowing to validate multiple query parameters.

    This validator splits comma-separated query parameter into lists,
    verifies their type and returns it directly, instead of returning a list
    containing a single element.

    Note that this validator uses ``voluptuous.Coerce`` internally and thus
    should not be used together with
    ``cloudkitty.utils.validation.get_string_type`` in python2.

    :param param_type: Type of the query parameter
    """
    def __init__(self, param_type):
        self._validate = lambda x: list(map(voluptuous.Coerce(param_type), x))

    def __call__(self, v):
        if not isinstance(v, list):
            v = [v]
        output = itertools.chain(*[elem.split(',') for elem in v])
        return self._validate(output)


class DictQueryParam(object):
    """Voluptuous helper to validate dict query params.

    This validator converts a dict query parameter to a python dict.

    :param key_type: Type of the dict keys
    :param val_type: Type of the dict values
    :param unique_values: Defaults to True. Set to True if each key should
                          contain only one value
    :type unique_values: bool
    """
    def __init__(self, key_type, val_type, unique_values=True):
        self._kval = voluptuous.Coerce(key_type)
        self._unique_val = unique_values

        if self._unique_val:
            self._vval = voluptuous.Coerce(val_type)
        else:
            def __vval(values):
                return [voluptuous.Coerce(val_type)(v) for v in values]
            self._vval = __vval

    @staticmethod
    def _append(output, key, val):
        if key in output.keys():
            output[key].append(val)
        else:
            output[key] = [val]
        return output

    def __call__(self, v):
        if not isinstance(v, list):
            v = [v]

        tokens = itertools.chain(*[elem.split(',') for elem in v])
        output = {}
        for token in tokens:
            try:
                key, val = token.split(':')
            except ValueError:  # Not enough or too many values to unpack
                raise voluptuous.DictInvalid(
                    'invalid key:value association {}'.format(token))

            if key in output.keys():
                if self._unique_val:
                    raise voluptuous.DictInvalid(
                        'key {} already provided'.format(key))

            if self._unique_val:
                output[key] = val
            else:
                output = self._append(output, key, val)

        return {self._kval(k): self._vval(v) for k, v in output.items()}


class SingleDictQueryParam(DictQueryParam):

    def __init__(self, key_type, val_type):
        super(SingleDictQueryParam, self).__init__(key_type=key_type,
                                                   val_type=val_type,
                                                   unique_values=True)


class MultiDictQueryParam(DictQueryParam):

    def __init__(self, key_type, val_type):
        super(MultiDictQueryParam, self).__init__(key_type=key_type,
                                                  val_type=val_type,
                                                  unique_values=False)


def add_input_schema(location, schema):
    """Add a voluptuous schema validation on a method's input

    Takes a dict which can be converted to a voluptuous schema as parameter,
    and validates the parameters with this schema. The "location" parameter
    is used to specify the parameters' location. Note that for query
    parameters, a ``MultiDict`` is returned by Flask. Thus, each dict key will
    contain a list. In order to ease interaction with unique query parameters,
    the ``SingleQueryParam`` voluptuous validator can be used::

        from cloudkitty.api.v2 import utils as api_utils
        @api_utils.add_input_schema('query', {
            voluptuous.Required('fruit'): api_utils.SingleQueryParam(str),
        })
        def put(self, fruit=None):
            return fruit


    To accept a list of query parameters, a ``MultiQueryParam`` can be used::

        from cloudkitty.api.v2 import utils as api_utils
        @api_utils.add_input_schema('query', {
            voluptuous.Required('fruit'): api_utils.MultiQueryParam(str),
        })
        def put(self, fruit=[]):
            for f in fruit:
                # Do something with the fruit

    :param location: Location of the args. Must be one of ['body', 'query']
    :type location: str
    :param schema: Schema to apply to the method's kwargs
    :type schema: dict
    """
    def decorator(f):
        try:
            s = getattr(f, 'input_schema')
            s = s.extend(schema)
            # The previous schema must be deleted or it will be called... [1/2]
            delattr(f, 'input_schema')
        except AttributeError:
            s = voluptuous.Schema(schema)

        def wrap(self, **kwargs):
            if hasattr(wrap, 'input_schema'):
                if location == 'body':
                    args = flask.request.get_json()
                elif location == 'query':
                    # NOTE(lpeschke): issues with to_dict in python3.7,
                    # see https://github.com/pallets/werkzeug/issues/1379
                    args = dict(flask.request.args.lists())
                try:
                    # ...here [2/2]
                    kwargs.update(wrap.input_schema(args))
                except voluptuous.Invalid as e:
                    raise exceptions.BadRequest(
                        "Invalid data '{a}' : {m} (path: '{p}')".format(
                            a=args, m=e.msg, p=str(e.path)))
            return f(self, **kwargs)

        wrap.input_schema = s
        return wrap

    return decorator


def paginated(func):
    """Helper function for pagination.

    Adds two parameters to the decorated function:
    * ``offset``: int >=0. Defaults to 0.
    * ``limit``: int >=1. Defaults to 100.

    Example usage::

       class Example(base.BaseResource):

           @api_utils.paginated
           @api_utils.add_output_schema({
               voluptuous.Required(
                   'message',
                   default='This is an example endpoint',
               ): validation_utils.get_string_type(),
           })
           def get(self, offset=0, limit=100):
               # [...]
    """
    return add_input_schema('query', {
        voluptuous.Required('offset', default=0): voluptuous.All(
            SingleQueryParam(int), voluptuous.Range(min=0)),
        voluptuous.Required('limit', default=100): voluptuous.All(
            SingleQueryParam(int), voluptuous.Range(min=1)),
    })(func)


def add_output_schema(schema):
    """Add a voluptuous schema validation on a method's output

    Example usage::

       class Example(base.BaseResource):

           @api_utils.add_output_schema({
               voluptuous.Required(
                   'message',
                   default='This is an example endpoint',
               ): validation_utils.get_string_type(),
           })
           def get(self):
               return {}

    :param schema: Schema to apply to the method's output
    :type schema: dict
    """
    schema = voluptuous.Schema(schema)

    def decorator(f):
        def wrap(*args, **kwargs):
            resp = f(*args, **kwargs)
            return schema(resp)
        return wrap
    return decorator


class ResourceNotFound(Exception):
    """Exception raised when a resource is not found"""

    def __init__(self, module, resource_class):
        msg = 'Resource {r} was not found in module {m}'.format(
            r=resource_class,
            m=module,
        )
        super(ResourceNotFound, self).__init__(msg)


def _load_resource(module, resource_class):
    try:
        module = importlib.import_module(module)
    except ImportError:
        raise ResourceNotFound(module, resource_class)

    resource = getattr(module, resource_class, None)
    if resource is None:
        raise ResourceNotFound(module, resource_class)
    return resource


def output_json(data, code, headers=None):
    """Helper function for api endpoint json serialization"""
    resp = flask.make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


def _get_blueprint_and_api(module_name):

    endpoint_name = module_name.split('.')[-1]

    blueprint = flask.Blueprint(endpoint_name, module_name)
    api = flask_restful.Api(blueprint)
    # Using cloudkitty.json instead of json for serialization
    api.representation('application/json')(output_json)

    return blueprint, api


def do_init(app, blueprint_name, resources):
    """Registers a new Blueprint containing one or several resources to app.

    :param app: Flask app in which the Blueprint should be registered
    :type app: flask.Flask
    :param blueprint_name: Name of the blueprint to create
    :type blueprint_name: str
    :param resources: Resources to add to the Blueprint's Api
    :type resources: list of dicts matching
                     ``cloudkitty.api.v2.RESOURCE_SCHEMA``
    """
    blueprint, api = _get_blueprint_and_api(blueprint_name)

    schema = voluptuous.Schema([v2_api.RESOURCE_SCHEMA])
    for resource_info in schema(resources):
        resource = _load_resource(resource_info['module'],
                                  resource_info['resource_class'])
        if resource_info['url'] and not resource_info['url'].startswith('/'):
            resource_info['url'] = '/' + resource_info['url']
        api.add_resource(resource, resource_info['url'])

    if not blueprint_name.startswith('/'):
        blueprint_name = '/' + blueprint_name
    app.register_blueprint(blueprint, url_prefix=blueprint_name)
