# CloudKitty devstack plugin
# Install and start **CloudKitty** service

# To enable a minimal set of CloudKitty services:
# - enable Ceilometer ;
# - add the following to the [[local|localrc]] section in the local.conf file:
#
#     enable_service ck-api ck-proc
#
# Dependencies:
# - functions
# - OS_AUTH_URL for auth in api
# - DEST, DATA_DIR set to the destination directory
# - SERVICE_PASSWORD, SERVICE_TENANT_NAME for auth in api
# - IDENTITY_API_VERSION for the version of Keystone
# - STACK_USER service user
# - HORIZON_DIR for horizon integration

# stack.sh
# ---------
# install_cloudkitty
# configure_cloudkitty
# init_cloudkitty
# start_cloudkitty
# stop_cloudkitty
# cleanup_cloudkitty
# install_python_cloudkittyclient

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set +o xtrace


# Support potential entry-points console scripts
if [[ -d $CLOUDKITTY_DIR/bin ]]; then
    CLOUDKITTY_BIN_DIR=$CLOUDKITTY_DIR/bin
else
    CLOUDKITTY_BIN_DIR=$(get_python_exec_prefix)
fi
CLOUDKITTY_UWSGI=$CLOUDKITTY_BIN_DIR/cloudkitty-api
if [ ${CLOUDKITTY_USE_UWSGI,,} == 'true' ]; then
    CLOUDKITTY_ENDPOINT=$CLOUDKITTY_SERVICE_PROTOCOL://$CLOUDKITTY_SERVICE_HOST/rating
else
    CLOUDKITTY_ENDPOINT=$CLOUDKITTY_SERVICE_PROTOCOL://$CLOUDKITTY_SERVICE_HOSTPORT
fi


# Functions
# ---------

# create_cloudkitty_accounts() - Set up common required cloudkitty accounts
# Tenant               User          Roles
# ------------------------------------------------------------------
# service              cloudkitty    admin        # if enabled
function create_cloudkitty_accounts {
    create_service_user "cloudkitty"

    local cloudkitty_service=$(get_or_create_service "cloudkitty" \
        "rating" "OpenStack Rating")
    get_or_create_endpoint $cloudkitty_service \
        "$REGION_NAME" $CLOUDKITTY_ENDPOINT

    # Create the rating role
    get_or_create_role "rating"

    # Make cloudkitty an admin
    get_or_add_user_project_role admin cloudkitty service

    # Make CloudKitty monitor demo project for rating purposes
    get_or_add_user_project_role rating cloudkitty demo
}

# Test if any CloudKitty services are enabled
# is_cloudkitty_enabled
function is_cloudkitty_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"ck-" ]] && return 0
    return 1
}

# cleanup_cloudkitty() - Remove residual data files, anything left over from previous
# runs that a clean run would need to clean up
function cleanup_cloudkitty {
    # Clean up dirs
    rm -rf $CLOUDKITTY_CONF_DIR/*
    rm -rf $CLOUDKITTY_OUTPUT_BASEPATH/*
    for i in $(find $CLOUDKITTY_ENABLED_DIR -iname '_[0-9]*.py' -printf '%f\n'); do
        rm -f "${CLOUDKITTY_HORIZON_ENABLED_DIR}/$i"
    done
    if [ ${CLOUDKITTY_USE_UWSGI,,} == 'true' ]; then
        remove_uwsgi_config "$CLOUDKITTY_UWSGI_CONF"
    fi
}


# configure_cloudkitty() - Set config files, create data dirs, etc
function configure_cloudkitty {
    setup_develop $CLOUDKITTY_DIR

    sudo mkdir -m 755 -p $CLOUDKITTY_CONF_DIR
    sudo chown $STACK_USER $CLOUDKITTY_CONF_DIR

    sudo mkdir -m 755 -p $CLOUDKITTY_API_LOG_DIR
    sudo chown $STACK_USER $CLOUDKITTY_API_LOG_DIR

    touch $CLOUDKITTY_CONF

    # generate policy sample file
    oslopolicy-sample-generator --config-file $CLOUDKITTY_DIR/etc/oslo-policy-generator/cloudkitty.conf --output-file $CLOUDKITTY_DIR/etc/cloudkitty/policy.yaml.sample
    cp $CLOUDKITTY_DIR/etc/cloudkitty/policy.yaml.sample "$CLOUDKITTY_CONF_DIR/policy.yaml"
    iniset $CLOUDKITTY_CONF oslo_policy policy_file 'policy.yaml'

    cp $CLOUDKITTY_DIR$CLOUDKITTY_CONF_DIR/api_paste.ini $CLOUDKITTY_CONF_DIR
    cp $CLOUDKITTY_DIR$CLOUDKITTY_CONF_DIR/metrics.yml $CLOUDKITTY_CONF_DIR
    iniset_rpc_backend cloudkitty $CLOUDKITTY_CONF DEFAULT

    iniset $CLOUDKITTY_CONF DEFAULT notification_topics 'notifications'
    iniset $CLOUDKITTY_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"
    iniset $CLOUDKITTY_CONF DEFAULT auth_strategy $CLOUDKITTY_AUTH_STRATEGY

    # auth
    iniset $CLOUDKITTY_CONF authinfos auth_type v3password
    iniset $CLOUDKITTY_CONF authinfos auth_protocol http
    iniset $CLOUDKITTY_CONF authinfos auth_url "$KEYSTONE_SERVICE_URI/v3"
    iniset $CLOUDKITTY_CONF authinfos identity_uri "$KEYSTONE_SERVICE_URI/v3"
    iniset $CLOUDKITTY_CONF authinfos username cloudkitty
    iniset $CLOUDKITTY_CONF authinfos password $SERVICE_PASSWORD
    iniset $CLOUDKITTY_CONF authinfos project_name $SERVICE_TENANT_NAME
    iniset $CLOUDKITTY_CONF authinfos tenant_name $SERVICE_TENANT_NAME
    iniset $CLOUDKITTY_CONF authinfos region_name $REGION_NAME
    iniset $CLOUDKITTY_CONF authinfos user_domain_name default
    iniset $CLOUDKITTY_CONF authinfos project_domain_name default
    iniset $CLOUDKITTY_CONF authinfos debug "$ENABLE_DEBUG_LOG_LEVEL"

    iniset $CLOUDKITTY_CONF fetcher backend $CLOUDKITTY_FETCHER
    iniset $CLOUDKITTY_CONF "fetcher_$CLOUDKITTY_FETCHER" auth_section authinfos
    if [[ "$CLOUDKITTY_FETCHER" == "keystone" ]]; then
        iniset $CLOUDKITTY_CONF fetcher_keystone keystone_version 3
    fi

    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "influxdb" ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 1 ]; then
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} user ${CLOUDKITTY_INFLUXDB_USER}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} password ${CLOUDKITTY_INFLUXDB_PASSWORD}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} database ${CLOUDKITTY_INFLUXDB_DATABASE}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} host ${CLOUDKITTY_INFLUXDB_HOST}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} port ${CLOUDKITTY_INFLUXDB_PORT}
    fi

    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "influxdb" ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 2 ]; then
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} host ${CLOUDKITTY_INFLUXDB_HOST}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} port ${CLOUDKITTY_INFLUXDB_PORT}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} url "http://${CLOUDKITTY_INFLUXDB_HOST}:${CLOUDKITTY_INFLUXDB_PORT}"
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} token ${CLOUDKITTY_INFLUXDB_PASSWORD}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} version 2
    fi

    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "elasticsearch" ]; then
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} host ${CLOUDKITTY_ELASTICSEARCH_HOST}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} index_name ${CLOUDKITTY_ELASTICSEARCH_INDEX}
    fi

    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "opensearch" ]; then
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} host ${CLOUDKITTY_OPENSEARCH_HOST}
        iniset $CLOUDKITTY_CONF storage_${CLOUDKITTY_STORAGE_BACKEND} index_name ${CLOUDKITTY_OPENSEARCH_INDEX}
    fi

    # collect
    iniset $CLOUDKITTY_CONF collect collector $CLOUDKITTY_COLLECTOR
    iniset $CLOUDKITTY_CONF "collector_${CLOUDKITTY_COLLECTOR}" auth_section authinfos
    iniset $CLOUDKITTY_CONF collect metrics_conf $CLOUDKITTY_CONF_DIR/$CLOUDKITTY_METRICS_CONF
    # DO NOT DO THIS IN PRODUCTION! This is done in order to get data quicker
    # when starting a devstack installation, but is NOT a recommended setting
    iniset $CLOUDKITTY_CONF collect wait_periods 0

    # output
    iniset $CLOUDKITTY_CONF output backend $CLOUDKITTY_OUTPUT_BACKEND
    iniset $CLOUDKITTY_CONF output basepath $CLOUDKITTY_OUTPUT_BASEPATH
    iniset $CLOUDKITTY_CONF output pipeline $CLOUDKITTY_OUTPUT_PIPELINE

    # storage
    iniset $CLOUDKITTY_CONF storage backend $CLOUDKITTY_STORAGE_BACKEND
    iniset $CLOUDKITTY_CONF storage version $CLOUDKITTY_STORAGE_VERSION

    # database
    local dburl=`database_connection_url cloudkitty`
    iniset $CLOUDKITTY_CONF database connection $dburl

    # keystone middleware
    configure_keystone_authtoken_middleware $CLOUDKITTY_CONF cloudkitty

    if [ ${CLOUDKITTY_USE_UWSGI,,} == 'true' ]; then
        write_uwsgi_config "$CLOUDKITTY_UWSGI_CONF" "$CLOUDKITTY_UWSGI" "/rating" "" "cloudkitty"
    fi
}

function wait_for_gnocchi() {
    local gnocchi_url=$(openstack --os-cloud devstack-admin endpoint list --service metric --interface public -c URL -f value)
    if ! wait_for_service $SERVICE_TIMEOUT $gnocchi_url; then
       die $LINENO "Waited for gnocchi too long."
    fi
}

# create_cloudkitty_data_dir() - Part of the init_cloudkitty() process
function create_cloudkitty_data_dir {
    # Create data dir
    sudo mkdir -p $CLOUDKITTY_DATA_DIR
    sudo chown $STACK_USER $CLOUDKITTY_DATA_DIR
    rm -rf $CLOUDKITTY_DATA_DIR/*
    # Create locks dir
    sudo mkdir -p $CLOUDKITTY_DATA_DIR/locks
    sudo chown $STACK_USER $CLOUDKITTY_DATA_DIR/locks
}

function create_influxdb_database {
    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "influxdb" ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 1 ]; then
        influx -execute "CREATE DATABASE ${CLOUDKITTY_INFLUXDB_DATABASE}"
    fi
    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "influxdb" ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 2 ]; then
        influx setup --username ${CLOUDKITTY_INFLUXDB_USER} --password ${CLOUDKITTY_INFLUXDB_PASSWORD} --token ${CLOUDKITTY_INFLUXDB_PASSWORD} --org openstack --bucket cloudkitty --force
    fi

}

function create_elasticsearch_index {
    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "elasticsearch" ]; then
        curl -XPUT "${CLOUDKITTY_ELASTICSEARCH_HOST}/${CLOUDKITTY_ELASTICSEARCH_INDEX}"
    fi
}

function create_opensearch_index {
    if [ "$CLOUDKITTY_STORAGE_BACKEND" == "opensearch" ]; then
        curl -XPUT "${CLOUDKITTY_OPENSEARCH_HOST}/${CLOUDKITTY_OPENSEARCH_INDEX}"
    fi
}

# init_cloudkitty() - Initialize CloudKitty database
function init_cloudkitty {
    # Delete existing cache
    sudo rm -rf $CLOUDKITTY_OUTPUT_BASEPATH
    sudo mkdir -p $CLOUDKITTY_OUTPUT_BASEPATH
    sudo chown $STACK_USER $CLOUDKITTY_OUTPUT_BASEPATH

    # (Re)create cloudkitty database
    recreate_database cloudkitty utf8

    create_influxdb_database
    create_elasticsearch_index
    create_opensearch_index

    # Migrate cloudkitty database
    upgrade_cloudkitty_database

    # Init the storage backend
    if [ $CLOUDKITTY_STORAGE_BACKEND == 'hybrid' ]; then
        wait_for_gnocchi
    fi
    $CLOUDKITTY_BIN_DIR/cloudkitty-storage-init

    create_cloudkitty_data_dir
}

function install_influx_ubuntu {
    local influxdb_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb_1.6.3_amd64.deb)
    sudo dpkg -i --skip-same-version ${influxdb_file}
}

function install_influx_v2_ubuntu {
    local influxdb_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb2_2.7.5-1_amd64.deb)
    sudo dpkg -i --skip-same-version ${influxdb_file}
    local influxcli_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-amd64.tar.gz)
    tar xvzf ${influxcli_file}
    sudo cp ./influx /usr/local/bin/
}

function install_influx_fedora {
    local influxdb_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb-1.6.3.x86_64.rpm)
    sudo yum localinstall -y ${influxdb_file}
}

function install_influx_v2_fedora {
    local influxdb_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.5-1.x86_64.rpm)
    sudo yum localinstall -y ${influxdb_file}
    local influxcli_file=$(get_extra_file https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-amd64.tar.gz)
    tar xvzf ${influxcli_file}
    sudo cp ./influx /usr/local/bin/
}

function install_influx {
    if is_ubuntu; then
        install_influx_ubuntu
    elif is_fedora; then
        install_influx_fedora
    else
        die $LINENO "Distribution must be Debian or Fedora-based"
    fi
    sudo cp -f "${CLOUDKITTY_DIR}"/devstack/files/influxdb.conf /etc/influxdb/influxdb.conf
    sudo systemctl start influxdb || sudo systemctl restart influxdb
}


function install_influx_v2 {
    if is_ubuntu; then
        install_influx_v2_ubuntu
    elif is_fedora; then
        install_influx_v2_fedora
    else
        die $LINENO "Distribution must be Debian or Fedora-based"
    fi
    sudo cp -f "${CLOUDKITTY_DIR}"/devstack/files/influxdb.conf /etc/influxdb/influxdb.conf
    sudo systemctl start influxdb || sudo systemctl restart influxdb
}

function install_elasticsearch_ubuntu {
    local opensearch_file=$(get_extra_file https://artifacts.opensearch.org/releases/bundle/opensearch/1.3.9/opensearch-1.3.9-linux-x64.deb)
    sudo dpkg -i --skip-same-version ${opensearch_file}
}

function install_elasticsearch_fedora {
    local opensearch_file=$(get_extra_file https://artifacts.opensearch.org/releases/bundle/opensearch/1.3.9/opensearch-1.3.9-linux-x64.rpm)
    sudo yum localinstall -y ${opensearch_file}
}

function install_elasticsearch {
    if is_ubuntu; then
        install_elasticsearch_ubuntu
    elif is_fedora; then
        install_elasticsearch_fedora
    else
        die $LINENO "Distribution must be Debian or Fedora-based"
    fi
    if ! sudo grep plugins.security.disabled /etc/opensearch/opensearch.yml >/dev/null; then
        echo "plugins.security.disabled: true" | sudo tee -a /etc/opensearch/opensearch.yml >/dev/null
    fi
    sudo systemctl enable opensearch
    sudo systemctl start opensearch || sudo systemctl restart opensearch
}

function install_opensearch_ubuntu {
    local opensearch_file=$(get_extra_file https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-linux-x64.deb)
    sudo dpkg -i --skip-same-version ${opensearch_file}
}

function install_opensearch_fedora {
    local opensearch_file=$(get_extra_file https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-linux-x64.rpm)
    sudo yum localinstall -y ${opensearch_file}
}

function install_opensearch {
    if is_ubuntu; then
        install_opensearch_ubuntu
    elif is_fedora; then
        install_opensearch_fedora
    else
        die $LINENO "Distribution must be Debian or Fedora-based"
    fi
    if ! sudo grep plugins.security.disabled /etc/opensearch/opensearch.yml >/dev/null; then
        echo "plugins.security.disabled: true" | sudo tee -a /etc/opensearch/opensearch.yml >/dev/null
    fi
    sudo systemctl enable opensearch
    sudo systemctl start opensearch || sudo systemctl restart opensearch
}

# install_cloudkitty() - Collect source and prepare
function install_cloudkitty {
    git_clone $CLOUDKITTY_REPO $CLOUDKITTY_DIR $CLOUDKITTY_BRANCH
    setup_develop $CLOUDKITTY_DIR
    if [ $CLOUDKITTY_STORAGE_BACKEND == 'influxdb' ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 1 ]; then
        install_influx
    elif [ $CLOUDKITTY_STORAGE_BACKEND == 'influxdb' ] && [ "$CLOUDKITTY_INFLUX_VERSION" == 2 ]; then
        install_influx_v2
    elif [ $CLOUDKITTY_STORAGE_BACKEND == 'elasticsearch' ]; then
        install_elasticsearch
    elif [ $CLOUDKITTY_STORAGE_BACKEND == 'opensearch' ]; then
        install_opensearch
    fi
    if [ ${CLOUDKITTY_USE_UWSGI,,} == 'true' ]; then
        pip_install uwsgi
    fi
}

# start_cloudkitty() - Start running processes, including screen
function start_cloudkitty {
    run_process ck-proc "$CLOUDKITTY_BIN_DIR/cloudkitty-processor --config-file=$CLOUDKITTY_CONF"
    if [ ${CLOUDKITTY_USE_UWSGI,,} == 'true' ]; then
        run_process ck-api "$CLOUDKITTY_BIN_DIR/uwsgi --ini $CLOUDKITTY_UWSGI_CONF"
    else
        run_process ck-api "$CLOUDKITTY_BIN_DIR/cloudkitty-api --host $CLOUDKITTY_SERVICE_HOST --port $CLOUDKITTY_SERVICE_PORT"
    fi
    echo "Waiting for ck-api ($CLOUDKITTY_SERVICE_HOST) to start..."
    if ! wait_for_service $SERVICE_TIMEOUT $CLOUDKITTY_ENDPOINT; then
        die $LINENO "ck-api did not start"
    fi
}

# stop_cloudkitty() - Stop running processes
function stop_cloudkitty {
    # Kill the cloudkitty screen windows
    if is_service_enabled ck-proc ; then
        stop_process ck-proc
    fi

    if is_service_enabled ck-api ; then
        # Kill the cloudkitty screen windows
        stop_process ck-api
    fi
}

# install_python_cloudkittyclient() - Collect source and prepare
function install_python_cloudkittyclient {
    # Install from git since we don't have a release (yet)
    git_clone_by_name "python-cloudkittyclient"
    setup_dev_lib "python-cloudkittyclient"
}

# install_cloudkitty_dashboard() - Collect source and prepare
function install_cloudkitty_dashboard {
    # Install from git since we don't have a release (yet)
    git_clone_by_name "cloudkitty-dashboard"
    setup_dev_lib "cloudkitty-dashboard"
}

# update_horizon_static() - Update Horizon static files with CloudKitty's one
function update_horizon_static {
    # Code taken from Horizon lib
    # Setup alias for django-admin which could be different depending on distro
    local django_admin
    if type -p django-admin > /dev/null; then
        django_admin=django-admin
    else
        django_admin=django-admin.py
    fi
    DJANGO_SETTINGS_MODULE=openstack_dashboard.settings \
        $django_admin collectstatic --noinput
    DJANGO_SETTINGS_MODULE=openstack_dashboard.settings \
        $django_admin compress --force
}

# Upgrade cloudkitty database
function upgrade_cloudkitty_database {
    $CLOUDKITTY_BIN_DIR/cloudkitty-dbsync upgrade
}

# configure_cloudkitty_dashboard() - Set config files, create data dirs, etc
function configure_cloudkitty_dashboard {
    sudo ln -s  $CLOUDKITTY_ENABLED_DIR/_[0-9]*.py \
        $CLOUDKITTY_HORIZON_ENABLED_DIR/
    update_horizon_static
}

if is_service_enabled ck-api; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing CloudKitty"
        install_cloudkitty
        install_python_cloudkittyclient
        if is_service_enabled horizon; then
            install_cloudkitty_dashboard
        fi
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring CloudKitty"
        configure_cloudkitty
        if is_service_enabled horizon; then
            configure_cloudkitty_dashboard
        fi
        if is_service_enabled key; then
            create_cloudkitty_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize cloudkitty
        echo_summary "Initializing CloudKitty"
        init_cloudkitty

        # Start the CloudKitty API and CloudKitty processor components
        echo_summary "Starting CloudKitty"
        start_cloudkitty
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_cloudkitty
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_cloudkitty
    fi
fi

# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
