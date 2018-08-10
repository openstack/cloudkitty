# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
# @author: Stéphane Albert
#
import abc
import decimal
import os
from unittest.case import SkipTest

from gabbi import fixture
import mock
from oslo_config import cfg
from oslo_config import fixture as conf_fixture
from oslo_db.sqlalchemy import utils
import oslo_messaging
from oslo_messaging import conffixture
from oslo_policy import opts as policy_opts
import six
from stevedore import driver
from stevedore import extension
import webob.dec
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api import app
from cloudkitty.api import middleware
from cloudkitty import db
from cloudkitty.db import api as ck_db_api
from cloudkitty import messaging
from cloudkitty import rating
from cloudkitty import storage
from cloudkitty.storage.v1.sqlalchemy import models
from cloudkitty import tests
from cloudkitty.tests import test_utils
from cloudkitty.tests.utils import is_functional_test
from cloudkitty import utils as ck_utils


INITIAL_TIMESTAMP = 1420070400


class UUIDFixture(fixture.GabbiFixture):
    def start_fixture(self):
        FAKE_UUID = '6c1b8a30-797f-4b7e-ad66-9879b79059fb'
        patcher = mock.patch(
            'oslo_utils.uuidutils.generate_uuid',
            return_value=FAKE_UUID)
        patcher.start()
        self.patcher = patcher

    def stop_fixture(self):
        self.patcher.stop()


@six.add_metaclass(abc.ABCMeta)
class BaseExtensionFixture(fixture.GabbiFixture):
    klass = None
    namespace = None
    stevedore_mgr = None
    assert_args = {}

    @abc.abstractmethod
    def setup_fake_modules(self):
        pass

    def start_fixture(self):
        fake_extensions = self.setup_fake_modules()
        self.mock = mock.patch(self.klass)
        fake_mgr = self.stevedore_mgr.make_test_instance(
            fake_extensions,
            self.namespace)
        self.patch = self.mock.start()
        self.patch.return_value = fake_mgr

    def stop_fixture(self):
        if not is_functional_test():
            self.patch.assert_called_with(
                self.namespace,
                **self.assert_args)
        self.mock.stop()


class CollectorExtensionsFixture(BaseExtensionFixture):
    klass = 'stevedore.driver.DriverManager'
    namespace = 'cloudkitty.collector.backends'
    stevedore_mgr = driver.DriverManager
    assert_args = {
        'invoke_kwds': {'period': 3600},
        'invoke_on_load': True}

    def setup_fake_modules(self):
        def fake_metric(start,
                        end=None,
                        project_id=None,
                        q_filter=None):
            return None

        fake_module1 = tests.FakeCollectorModule()
        fake_module1.collector_name = 'fake1'
        fake_module1.get_compute = fake_metric
        fake_module2 = tests.FakeCollectorModule()
        fake_module2.collector_name = 'fake2'
        fake_module2.get_volume = fake_metric
        fake_module3 = tests.FakeCollectorModule()
        fake_module3.collector_name = 'fake3'
        fake_module3.get_compute = fake_metric
        fake_extensions = [
            extension.Extension(
                'fake1',
                'cloudkitty.tests.FakeCollectorModule1',
                None,
                fake_module1),
            extension.Extension(
                'fake2',
                'cloudkitty.tests.FakeCollectorModule2',
                None,
                fake_module2),
            extension.Extension(
                'fake3',
                'cloudkitty.tests.FakeCollectorModule3',
                None,
                fake_module3)]
        return fake_extensions[0]


class RatingModulesFixture(BaseExtensionFixture):
    klass = 'stevedore.extension.ExtensionManager'
    namespace = 'cloudkitty.rating.processors'
    stevedore_mgr = extension.ExtensionManager
    assert_args = {
        'invoke_on_load': True}

    def setup_fake_modules(self):
        class FakeConfigController(rating.RatingRestControllerBase):
            _custom_actions = {
                'test': ['GET']
            }

            @wsme_pecan.wsexpose(wtypes.text)
            def get_test(self):
                """Return the list of every mapping type available.

                """
                return 'OK'

        fake_module1 = tests.FakeRatingModule()
        fake_module1.module_name = 'fake1'
        fake_module1.set_priority(3)
        fake_module2 = tests.FakeRatingModule()
        fake_module2.module_name = 'fake2'
        fake_module2.config_controller = FakeConfigController
        fake_module2.set_priority(1)
        fake_module3 = tests.FakeRatingModule()
        fake_module3.module_name = 'fake3'
        fake_module3.set_priority(2)
        fake_extensions = [
            extension.Extension(
                'fake1',
                'cloudkitty.tests.FakeRatingModule1',
                None,
                fake_module1),
            extension.Extension(
                'fake2',
                'cloudkitty.tests.FakeRatingModule2',
                None,
                fake_module2),
            extension.Extension(
                'fake3',
                'cloudkitty.tests.FakeRatingModule3',
                None,
                fake_module3)]
        return fake_extensions


class ConfigFixture(fixture.GabbiFixture):
    auth_strategy = 'noauth'

    def start_fixture(self):
        self.conf = None
        conf = conf_fixture.Config().conf
        policy_opts.set_defaults(conf)
        msg_conf = conffixture.ConfFixture(conf)
        msg_conf.transport_url = 'fake:/'
        conf.import_group('api', 'cloudkitty.api.app')
        conf.set_override('auth_strategy', self.auth_strategy)
        conf.set_override('connection', 'sqlite:///', 'database')
        conf.set_override('policy_file',
                          os.path.abspath('etc/cloudkitty/policy.json'),
                          group='oslo_policy')
        conf.set_override('api_paste_config',
                          os.path.abspath(
                              'cloudkitty/tests/gabbi/gabbi_paste.ini')
                          )
        conf.import_group('storage', 'cloudkitty.storage')
        conf.set_override('backend', 'sqlalchemy', 'storage')
        conf.set_override('version', '1', 'storage')
        self.conf = conf
        self.conn = ck_db_api.get_instance()
        migration = self.conn.get_migration()
        migration.upgrade('head')

    def stop_fixture(self):
        if self.conf:
            self.conf.reset()
        db.get_engine().dispose()


class ConfigFixtureKeystoneAuth(ConfigFixture):
    auth_strategy = 'keystone'

    def start_fixture(self):
        # Mocking the middleware process_request which check for credentials
        # here, the only check done is that the hardcoded token is the one
        # send by the query. If not, 401, else 200.
        def _mock_proc_request(self, request):
            token = 'c93e3e31342e4e32ba201fd3d70878b5'
            http_code = 401
            if 'X-Auth-Token' in request.headers and \
               request.headers['X-Auth-Token'] == token:
                http_code = 200

            return webob.Response(
                status_code=http_code,
                content_type='application/json'
            )

        self._orig_func = middleware.auth_token.AuthProtocol.process_request
        middleware.auth_token.AuthProtocol.process_request = _mock_proc_request

        super(ConfigFixtureKeystoneAuth, self).start_fixture()

    def stop_fixture(self):
        super(ConfigFixtureKeystoneAuth, self).stop_fixture()
        middleware.auth_token.AuthProtocol.process_request = self._orig_func


class BaseFakeRPC(fixture.GabbiFixture):
    endpoint = None

    def start_fixture(self):
        messaging.setup()
        target = oslo_messaging.Target(topic='cloudkitty',
                                       server=cfg.CONF.host,
                                       version='1.0')
        endpoints = [
            self.endpoint()
        ]
        self.server = messaging.get_server(target, endpoints)
        self.server.start()

    def stop_fixture(self):
        self.server.stop()


class QuoteFakeRPC(BaseFakeRPC):
    class FakeRPCEndpoint(object):
        target = oslo_messaging.Target(namespace='rating',
                                       version='1.0')

        def quote(self, ctxt, res_data):
            return str(1.0)

    endpoint = FakeRPCEndpoint


class BaseStorageDataFixture(fixture.GabbiFixture):
    def create_fake_data(self, begin, end):
        data = [{
            "period": {
                "begin": begin,
                "end": end},
            "usage": {
                "cpu": [
                    {
                        "desc": {
                            "dummy": True,
                            "fake_meta": 1.0},
                        "vol": {
                            "qty": 1,
                            "unit": "nothing"},
                        "rating": {
                            "price": decimal.Decimal('1.337')}}]}}, {
            "period": {
                "begin": begin,
                "end": end},
            "usage": {
                "image.size": [
                    {
                        "desc": {
                            "dummy": True,
                            "fake_meta": 1.0},
                        "vol": {
                            "qty": 1,
                            "unit": "nothing"},
                        "rating": {
                            "price": decimal.Decimal('0.121')}}]}}]
        return data

    def start_fixture(self):
        auth = mock.patch(
            'keystoneauth1.loading.load_auth_from_conf_options',
            return_value=dict())
        session = mock.patch(
            'keystoneauth1.loading.load_session_from_conf_options',
            return_value=dict())
        with auth:
            with session:
                self.storage = storage.get_storage(conf=test_utils.load_conf())
        self.storage.init()
        self.initialize_data()

    def stop_fixture(self):
        model = models.RatedDataFrame
        session = db.get_session()
        q = utils.model_query(
            model,
            session)
        q.delete()


class StorageDataFixture(BaseStorageDataFixture):
    def initialize_data(self):
        nodata_duration = (24 * 3 + 12) * 3600
        tenant_list = ['8f82cc70-e50c-466e-8624-24bdea811375',
                       '7606a24a-b8ad-4ae0-be6c-3d7a41334a2e']
        data_ts = INITIAL_TIMESTAMP + nodata_duration + 3600
        data_duration = (24 * 2 + 8) * 3600
        for i in range(data_ts,
                       data_ts + data_duration,
                       3600):
            data = self.create_fake_data(i, i + 3600)
            self.storage.push(data, tenant_list[0])
        half_duration = int(data_duration / 2)
        for i in range(data_ts,
                       data_ts + half_duration,
                       3600):
            data = self.create_fake_data(i, i + 3600)
            self.storage.push(data, tenant_list[1])


class NowStorageDataFixture(BaseStorageDataFixture):
    def initialize_data(self):
        begin = ck_utils.get_month_start_timestamp()
        for i in range(begin,
                       begin + 3600 * 12,
                       3600):
            data = self.create_fake_data(i, i + 3600)
            self.storage.push(data,
                              '3d9a1b33-482f-42fd-aef9-b575a3da9369')


class CORSConfigFixture(fixture.GabbiFixture):
    """Inject mock configuration for the CORS middleware."""

    def start_fixture(self):
        # Here we monkeypatch GroupAttr.__getattr__, necessary because the
        # paste.ini method of initializing this middleware creates its own
        # ConfigOpts instance, bypassing the regular config fixture.

        def _mock_getattr(instance, key):
            if key != 'allowed_origin':
                return self._original_call_method(instance, key)
            return "http://valid.example.com"

        self._original_call_method = cfg.ConfigOpts.GroupAttr.__getattr__
        cfg.ConfigOpts.GroupAttr.__getattr__ = _mock_getattr

    def stop_fixture(self):
        """Remove the monkeypatch."""
        cfg.ConfigOpts.GroupAttr.__getattr__ = self._original_call_method


class MetricsConfFixture(fixture.GabbiFixture):
    """Inject Metrics configuration mock to the get_metrics_conf() function"""

    def start_fixture(self):
        self._original_function = ck_utils.load_conf
        ck_utils.load_conf = mock.Mock(
            return_value=tests.samples.METRICS_CONF,
        )

    def stop_fixture(self):
        """Remove the get_metrics_conf() monkeypatch."""
        ck_utils.load_conf = self._original_function


class SkipIfFunctional(fixture.GabbiFixture):

    def start_fixture(self):
        if is_functional_test():
            raise SkipTest


def setup_app():
    messaging.setup()
    # FIXME(sheeprine): Extension fixtures are interacting with transformers
    # loading, since collectors are not needed here we shunt them
    no_collector = mock.patch(
        'cloudkitty.collector.get_collector',
        return_value=None)
    with no_collector:
        return app.load_app()
