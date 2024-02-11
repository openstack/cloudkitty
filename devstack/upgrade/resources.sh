#!/bin/bash

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin

set -o xtrace

CLOUDKITTY_GRENADE_DIR=$(dirname $0)

CK_SERVICE_NAME='test_service'
CK_FIELD_NAME='test_field'
CK_MAPPING_VALUE='test_value'

function create {
    CK_SERVICE_ID=$(openstack rating hashmap service create $CK_SERVICE_NAME -c 'Service ID' -f value)
    CK_FIELD_ID=$(openstack rating hashmap field create $CK_SERVICE_ID $CK_FIELD_NAME -c 'Field ID' -f value)
    openstack rating hashmap mapping create --field-id $CK_FIELD_ID --value $CK_MAPPING_VALUE 3

    echo "CloudKitty create: SUCCESS"
}

function verify {
    CK_SERVICE_NAME_VERIFY=$(openstack rating hashmap service list -c 'Name' -f value)
    if [ $CK_SERVICE_NAME_VERIFY != $CK_SERVICE_NAME ]; then
         echo "CloudKitty verify invalid service name. Expected $CK_SERVICE_NAME got $CK_SERVICE_NAME_VERIFY."
         errexit
    fi
    CK_SERVICE_ID=$(openstack rating hashmap service list -c 'Service ID' -f value)
    CK_FIELD_NAME_VERIFY=$(openstack rating hashmap field list $CK_SERVICE_ID -c 'Name' -f value)
    if [ $CK_FIELD_NAME_VERIFY != $CK_FIELD_NAME ]; then
         echo "CloudKitty verify invalid field name. Expected $CK_FIELD_NAME got $CK_FIELD_NAME_VERIFY."
         errexit
    fi
    CK_FIELD_ID=$(openstack rating hashmap field list $CK_SERVICE_ID -c 'Field ID' -f value)
    CK_MAPPING_VALUE_VERIFY=$(openstack rating hashmap mapping list --field-id $CK_FIELD_ID -c 'Value' -f value)
    if [ $CK_MAPPING_VALUE_VERIFY != $CK_MAPPING_VALUE ]; then
         echo "CloudKitty verify invalid mapping value. Expected $CK_MAPPING_VALUE got $CK_MAPPING_VALUE_VERIFY."
         errexit
    fi

    echo "CloudKitty verify: SUCCESS"
}

function verify_noapi {
    echo "CloudKitty verify_noapi: SUCCESS"
}

function destroy {
    CK_SERVICE_ID=$(openstack rating hashmap service list -c 'Service ID' -f value)
    openstack rating hashmap service delete $CK_SERVICE_ID
    echo "CloudKitty destroy: SUCCESS"
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify_noapi")
        verify_noapi
        ;;
    "verify")
        verify
        ;;
    "destroy")
        destroy
        ;;
    "force_destroy")
        set +o errexit
        destroy
        ;;
esac
