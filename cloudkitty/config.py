from oslo.config import cfg


auth_opts = [
    cfg.StrOpt('username',
               default='',
               help='OpenStack username.'),
    cfg.StrOpt('password',
               default='',
               help='OpenStack password.'),
    cfg.StrOpt('tenant',
               default='',
               help='OpenStack tenant.'),
    cfg.StrOpt('region',
               default='',
               help='OpenStack region.'),
    cfg.StrOpt('url',
               default='',
               help='OpenStack auth URL.'), ]

collect_opts = [
    cfg.StrOpt('collector',
               default='cloudkitty.collector.ceilometer.CeilometerCollector',
               help='Data collector.'),
    cfg.IntOpt('window',
               default=1800,
               help='Number of samples to collect per call.'),
    cfg.IntOpt('period',
               default=3600,
               help='Billing period in seconds.'),
    cfg.ListOpt('services',
                default=['compute'],
                help='Services to monitor.'), ]

state_opts = [
    cfg.StrOpt('backend',
               default='cloudkitty.backend.file.FileBackend',
               help='Backend for the state manager.'),
    cfg.StrOpt('basepath',
               default='/var/lib/cloudkitty/states/',
               help='Storage directory for the file state backend.'), ]

billing_opts = [
    cfg.ListOpt('pipeline',
                default=['cloudkitty.billing.hash.BasicHashMap',
                         'cloudkitty.billing.noop.Noop'],
                help='Billing pipeline modules.'), ]

output_opts = [
    cfg.StrOpt('backend',
               default='cloudkitty.backend.file.FileBackend',
               help='Backend for the output manager.'),
    cfg.StrOpt('basepath',
               default='/var/lib/cloudkitty/states/',
               help='Storage directory for the file output backend.'),
    cfg.ListOpt('pipeline',
                default=['cloudkitty.writer.osrf.OSRFBackend'],
                help='Output pipeline'), ]


cfg.CONF.register_opts(auth_opts, 'auth')
cfg.CONF.register_opts(collect_opts, 'collect')
cfg.CONF.register_opts(state_opts, 'state')
cfg.CONF.register_opts(billing_opts, 'billing')
cfg.CONF.register_opts(output_opts, 'output')
