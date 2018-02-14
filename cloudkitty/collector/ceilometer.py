# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
import decimal

from ceilometerclient import client as cclient
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import units

from cloudkitty import collector
from cloudkitty import utils as ck_utils


LOG = logging.getLogger(__name__)

CEILOMETER_COLLECTOR_OPTS = 'ceilometer_collector'
ceilometer_collector_opts = ks_loading.get_auth_common_conf_options()

cfg.CONF.register_opts(ceilometer_collector_opts, CEILOMETER_COLLECTOR_OPTS)
ks_loading.register_session_conf_options(
    cfg.CONF,
    CEILOMETER_COLLECTOR_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    CEILOMETER_COLLECTOR_OPTS)
CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)


class ResourceNotFound(Exception):
    """Raised when the resource doesn't exist."""

    def __init__(self, resource_type, resource_id):
        super(ResourceNotFound, self).__init__(
            "No such resource: %s, type: %s" % (resource_id, resource_type))
        self.resource_id = resource_id
        self.resource_type = resource_type


class CeilometerResourceCacher(object):
    def __init__(self):
        self._resource_cache = {}

    def add_resource_detail(self, resource_type, resource_id, resource_data):
        if resource_type not in self._resource_cache:
            self._resource_cache[resource_type] = {}
        self._resource_cache[resource_type][resource_id] = resource_data
        return self._resource_cache[resource_type][resource_id]

    def has_resource_detail(self, resource_type, resource_id):
        if resource_type in self._resource_cache:
            if resource_id in self._resource_cache[resource_type]:
                return True
        return False

    def get_resource_detail(self, resource_type, resource_id):
        try:
            resource = self._resource_cache[resource_type][resource_id]
            return resource
        except KeyError:
            raise ResourceNotFound(resource_type, resource_id)


class CeilometerCollector(collector.BaseCollector):
    collector_name = 'ceilometer'
    dependencies = ('CeilometerTransformer',
                    'CloudKittyFormatTransformer')

    units_mappings = {
        'compute': 'instance',
        'image': 'MiB',
        'volume': 'GiB',
        'network.bw.out': 'MB',
        'network.bw.in': 'MB',
        'network.floating': 'ip',
        'radosgw.usage': 'GiB'
    }

    def __init__(self, transformers, **kwargs):
        super(CeilometerCollector, self).__init__(transformers, **kwargs)

        self.t_ceilometer = self.transformers['CeilometerTransformer']
        self.t_cloudkitty = self.transformers['CloudKittyFormatTransformer']

        self._cacher = CeilometerResourceCacher()

        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            CEILOMETER_COLLECTOR_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            CEILOMETER_COLLECTOR_OPTS,
            auth=self.auth)
        self._conn = cclient.get_client(
            '2',
            session=self.session)

    @classmethod
    def get_metadata(cls, resource_name, transformers):
        info = super(CeilometerCollector, cls).get_metadata(resource_name,
                                                            transformers)
        try:
            info["metadata"].extend(transformers['CeilometerTransformer']
                                    .get_metadata(resource_name))

            try:
                tmp = METRICS_CONF['metrics_units'][resource_name]
                info['unit'] = list(tmp.values())[0]['unit']
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                info['unit'] = cls.units_mappings[resource_name]

        except KeyError:
            pass
        return info

    def gen_filter(self, op='eq', **kwargs):
        """Generate ceilometer filter from kwargs."""
        q_filter = []
        for kwarg in kwargs:
            q_filter.append({'field': kwarg, 'op': op, 'value': kwargs[kwarg]})
        return q_filter

    def prepend_filter(self, prepend, **kwargs):
        """Filter composer."""
        q_filter = {}
        for kwarg in kwargs:
            q_filter[prepend + kwarg] = kwargs[kwarg]
        return q_filter

    def user_metadata_filter(self, op='eq', **kwargs):
        """Create user_metadata filter from kwargs."""
        user_filter = {}
        for kwarg in kwargs:
            field = kwarg
            # Auto replace of . to _ to match ceilometer behaviour
            if '.' in field:
                field = field.replace('.', '_')
            user_filter[field] = kwargs[kwarg]
        user_filter = self.prepend_filter('user_metadata.', **user_filter)
        return self.metadata_filter(op, **user_filter)

    def metadata_filter(self, op='eq', **kwargs):
        """Create metadata filter from kwargs."""
        meta_filter = self.prepend_filter('metadata.', **kwargs)
        return self.gen_filter(op, **meta_filter)

    def resources_stats(self,
                        meter,
                        start,
                        end=None,
                        project_id=None,
                        q_filter=None):
        """Resources statistics during the timespan."""
        start_iso = ck_utils.ts2iso(start)
        req_filter = self.gen_filter(op='ge', timestamp=start_iso)
        if project_id:
            req_filter.extend(self.gen_filter(project=project_id))
        if end:
            end_iso = ck_utils.ts2iso(end)
            req_filter.extend(self.gen_filter(op='le', timestamp=end_iso))
        if isinstance(q_filter, list):
            req_filter.extend(q_filter)
        elif q_filter:
            req_filter.append(q_filter)
        resources_stats = self._conn.statistics.list(meter_name=meter,
                                                     period=0, q=req_filter,
                                                     groupby=['resource_id'])
        return resources_stats

    def active_resources(self,
                         meter,
                         start,
                         end=None,
                         project_id=None,
                         q_filter=None):
        """Resources that were active during the timespan."""
        resources_stats = self.resources_stats(meter,
                                               start,
                                               end,
                                               project_id,
                                               q_filter)
        return [resource.groupby['resource_id']
                for resource in resources_stats]

    def get_compute(self, start, end=None, project_id=None, q_filter=None):
        active_instance_ids = self.active_resources('cpu', start, end,
                                                    project_id, q_filter)
        compute_data = []
        for instance_id in active_instance_ids:
            if not self._cacher.has_resource_detail('compute', instance_id):
                raw_resource = self._conn.resources.get(instance_id)
                instance = self.t_ceilometer.strip_resource_data('compute',
                                                                 raw_resource)
                self._cacher.add_resource_detail('compute',
                                                 instance_id,
                                                 instance)
            instance = self._cacher.get_resource_detail('compute',
                                                        instance_id)

            try:
                met = list(METRICS_CONF['metrics_units']['compute'].values())
                compute_data.append(self.t_cloudkitty.format_item(
                    instance,
                    met[0]['unit'],
                    1,
                ))
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                compute_data.append(self.t_cloudkitty.format_item(
                    instance,
                    self.units_mappings['compute'],
                    1,
                ))
        if not compute_data:
            raise collector.NoDataCollected(self.collector_name, 'compute')
        return self.t_cloudkitty.format_service('compute', compute_data)

    def get_image(self, start, end=None, project_id=None, q_filter=None):
        active_image_stats = self.resources_stats('image.size',
                                                  start,
                                                  end,
                                                  project_id,
                                                  q_filter)
        image_data = []
        for image_stats in active_image_stats:
            image_id = image_stats.groupby['resource_id']
            if not self._cacher.has_resource_detail('image', image_id):
                raw_resource = self._conn.resources.get(image_id)
                image = self.t_ceilometer.strip_resource_data('image',
                                                              raw_resource)
                self._cacher.add_resource_detail('image',
                                                 image_id,
                                                 image)
            image = self._cacher.get_resource_detail('image',
                                                     image_id)

            # Unit conversion
            try:
                conv_data = METRICS_CONF['metrics_units']['image']
                image_size_mb = ck_utils.convert_unit(
                    decimal.Decimal(image_stats.max),
                    conv_data['image.size'].get('factor', 1),
                    conv_data['image.size'].get('offset', 0),
                )
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated hardcoded method.')
                image_size_mb = decimal.Decimal(image_stats.max) / units.Mi

            try:
                met = list(METRICS_CONF['metrics_units']['image'].values())
                image_data.append(self.t_cloudkitty.format_item(
                    image,
                    met[0]['unit'],
                    image_size_mb,
                ))
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                image_data.append(self.t_cloudkitty.format_item(
                    image,
                    self.units_mappings['image'],
                    image_size_mb,
                ))

        if not image_data:
            raise collector.NoDataCollected(self.collector_name, 'image')
        return self.t_cloudkitty.format_service('image', image_data)

    def get_volume(self, start, end=None, project_id=None, q_filter=None):
        active_volume_stats = self.resources_stats('volume.size',
                                                   start,
                                                   end,
                                                   project_id,
                                                   q_filter)
        volume_data = []
        for volume_stats in active_volume_stats:
            volume_id = volume_stats.groupby['resource_id']
            if not self._cacher.has_resource_detail('volume',
                                                    volume_id):
                raw_resource = self._conn.resources.get(volume_id)
                volume = self.t_ceilometer.strip_resource_data('volume',
                                                               raw_resource)
                self._cacher.add_resource_detail('volume',
                                                 volume_id,
                                                 volume)
            volume = self._cacher.get_resource_detail('volume',
                                                      volume_id)

            # Unit conversion
            try:
                conv_data = METRICS_CONF['metrics_units']['volume']
                volume_stats.max = ck_utils.convert_unit(
                    decimal.Decimal(volume_stats.max),
                    conv_data['volume.size'].get('factor', 1),
                    conv_data['volume.size'].get('offset', 0),
                )

                volume_data.append(self.t_cloudkitty.format_item(
                    volume,
                    conv_data['volume.size']['unit'],
                    volume_stats.max,
                ))
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                volume_data.append(self.t_cloudkitty.format_item(
                    volume,
                    self.units_mappings['volume'],
                    volume_stats.max,
                ))

        if not volume_data:
            raise collector.NoDataCollected(self.collector_name, 'volume')
        return self.t_cloudkitty.format_service('volume', volume_data)

    def _get_network_bw(self,
                        direction,
                        start,
                        end=None,
                        project_id=None,
                        q_filter=None):
        if direction == 'in':
            resource_type = 'network.incoming.bytes'
        else:
            direction = 'out'
            resource_type = 'network.outgoing.bytes'
        active_tap_stats = self.resources_stats(resource_type,
                                                start,
                                                end,
                                                project_id,
                                                q_filter)
        bw_data = []
        for tap_stat in active_tap_stats:
            tap_id = tap_stat.groupby['resource_id']
            if not self._cacher.has_resource_detail('network.tap',
                                                    tap_id):
                raw_resource = self._conn.resources.get(tap_id)
                tap = self.t_ceilometer.strip_resource_data(
                    'network.tap',
                    raw_resource)
                self._cacher.add_resource_detail('network.tap',
                                                 tap_id,
                                                 tap)
            tap = self._cacher.get_resource_detail('network.tap',
                                                   tap_id)

            # Unit conversion
            try:
                conv = METRICS_CONF['metrics_units']['network.bw.' + direction]
                tap_bw_mb = ck_utils.convert_unit(
                    decimal.Decimal(tap_stat.max),
                    conv[resource_type].get('factor', 1),
                    conv[resource_type].get('offset', 0),
                )
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated hardcoded method.')
                tap_bw_mb = decimal.Decimal(tap_stat.max) / units.M

            try:
                met = METRICS_CONF['metrics_units']['network.bw.' + direction]
                bw_data.append(self.t_cloudkitty.format_item(
                    tap,
                    list(met.values())[0]['unit'],
                    tap_bw_mb,
                ))
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                bw_data.append(self.t_cloudkitty.format_item(
                    tap,
                    self.units_mappings['network.bw.' + direction],
                    tap_bw_mb,
                ))

        ck_res_name = 'network.bw.{}'.format(direction)
        if not bw_data:
            raise collector.NoDataCollected(self.collector_name,
                                            ck_res_name)
        return self.t_cloudkitty.format_service(ck_res_name,
                                                bw_data)

    def get_network_bw_out(self,
                           start,
                           end=None,
                           project_id=None,
                           q_filter=None):
        return self._get_network_bw('out', start, end, project_id, q_filter)

    def get_network_bw_in(self,
                          start,
                          end=None,
                          project_id=None,
                          q_filter=None):
        return self._get_network_bw('in', start, end, project_id, q_filter)

    def get_network_floating(self,
                             start,
                             end=None,
                             project_id=None,
                             q_filter=None):
        active_floating_ids = self.active_resources('ip.floating',
                                                    start,
                                                    end,
                                                    project_id,
                                                    q_filter)
        floating_data = []
        for floating_id in active_floating_ids:
            if not self._cacher.has_resource_detail('network.floating',
                                                    floating_id):
                raw_resource = self._conn.resources.get(floating_id)
                floating = self.t_ceilometer.strip_resource_data(
                    'network.floating',
                    raw_resource)
                self._cacher.add_resource_detail('network.floating',
                                                 floating_id,
                                                 floating)
            floating = self._cacher.get_resource_detail('network.floating',
                                                        floating_id)

            try:
                metric = METRICS_CONF['metrics_units']['network.floating']
                floating_data.append(self.t_cloudkitty.format_item(
                    floating,
                    list(metric.values())[0]['unit'],
                    1,
                ))
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                floating_data.append(self.t_cloudkitty.format_item(
                    floating,
                    self.units_mappings['network.floating'],
                    1,
                ))

        if not floating_data:
            raise collector.NoDataCollected(self.collector_name,
                                            'network.floating')
        return self.t_cloudkitty.format_service('network.floating',
                                                floating_data)

    def get_radosgw_usage(self,
                          start,
                          end=None,
                          project_id=None,
                          q_filter=None):
        active_rgw_stats = self.resources_stats('radosgw.objects.size', start,
                                                end, project_id, q_filter)
        rgw_data = []
        for rgw_stats in active_rgw_stats:
            rgw_id = rgw_stats.groupby['resource_id']
            if not self._cacher.has_resource_detail('radosgw.usage', rgw_id):
                raw_resource = self._conn.resources.get(rgw_id)
                rgw = self.t_ceilometer.strip_resource_data('radosgw.usage',
                                                            raw_resource)
                self._cacher.add_resource_detail('radosgw.usage', rgw_id, rgw)
            rgw = self._cacher.get_resource_detail('radosgw.usage', rgw_id)

            # Unit conversion
            try:
                conv_data = METRICS_CONF['metrics_units']['radosgw.usage']
                rgw_size = ck_utils.convert_unit(
                    decimal.Decimal(rgw_stats.max),
                    conv_data['radosgw.object.size'].get('factor', 1),
                    conv_data['radosgw.object.size'].get('offset', 0),
                )

                rgw_data.append(
                    self.t_cloudkitty.format_item(
                        rgw,
                        conv_data['rados.objects.size']['unit'],
                        rgw_size,
                    )
                )
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated hardcoded method.')
                rgw_size = decimal.Decimal(rgw_stats.max) / units.Gi
                rgw_data.append(
                    self.t_cloudkitty.format_item(
                        rgw,
                        self.units_mappings['radosgw.usage'],
                        rgw_size,
                    )
                )

        if not rgw_data:
            raise collector.NoDataCollected(self.collector_name,
                                            'radosgw.usage')
        return self.t_cloudkitty.format_service('radosgw.usage', rgw_data)
