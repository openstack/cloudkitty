====================
Policy configuration
====================

Configuration
~~~~~~~~~~~~~

.. warning::

   JSON formatted policy file is deprecated since Cloudkitty 14.0.0 (Wallaby).
   This `oslopolicy-convert-json-to-yaml`__ tool will migrate your existing
   JSON-formatted policy file to YAML in a backward-compatible way.

.. __: https://docs.openstack.org/oslo.policy/latest/cli/oslopolicy-convert-json-to-yaml.html

The following is an overview of all available policies in Cloudkitty.
For a sample configuration file, refer to :doc:`samples/policy-yaml`.

.. show-policy::
      :config-file: ../../etc/oslo-policy-generator/cloudkitty.conf
