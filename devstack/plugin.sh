# CloudKitty devstack plugin
# Install and start **CloudKitty** service

# To enable a minimal set of CloudKitty services:
# - enable Ceilometer ;
# - add the following to localrc:
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


# Defaults
# --------

# Set up default directories
CLOUDKITTY_DIR=$DEST/cloudkitty
CLOUDKITTY_CONF_DIR=/etc/cloudkitty
CLOUDKITTY_CONF=$CLOUDKITTY_CONF_DIR/cloudkitty.conf
CLOUDKITTY_API_LOG_DIR=/var/log/cloudkitty
CLOUDKITTY_AUTH_CACHE_DIR=${CLOUDKITTY_AUTH_CACHE_DIR:-/var/cache/cloudkitty}
CLOUDKITTY_REPORTS_DIR=${DATA_DIR}/cloudkitty/reports
# Horizon enabled file
CLOUDKITTY_DASHBOARD=$DEST/cloudkitty-dashboard/cloudkittydashboard
CLOUDKITTY_ENABLED_FILE=${CLOUDKITTY_ENABLED_FILE:-${CLOUDKITTY_DASHBOARD}/_90_enable_ck.py}
CLOUDKITTY_HORIZON_ENABLED_FILE=${CLOUDKITTY_HORIZON_ENABLED_FILE:-$HORIZON_DIR/openstack_dashboard/enabled/_90_enable_ck.py}

# Support potential entry-points console scripts
if [[ -d $CLOUDKITTY_DIR/bin ]]; then
    CLOUDKITTY_BIN_DIR=$CLOUDKITTY_DIR/bin
else
    CLOUDKITTY_BIN_DIR=$(get_python_exec_prefix)
fi

# Set up database backend
CLOUDKITTY_BACKEND=${CLOUDKITTY_BACKEND:-sqlite}

# Set cloudkitty repository
CLOUDKITTY_REPO=${CLOUDKITTY_REPO:-${GIT_BASE}/stackforge/cloudkitty.git}
CLOUDKITTY_BRANCH=${CLOUDKITTY_BRANCH:-master}

# Set CloudKitty connection info
CLOUDKITTY_SERVICE_HOST=${CLOUDKITTY_SERVICE_HOST:-$SERVICE_HOST}
CLOUDKITTY_SERVICE_PORT=${CLOUDKITTY_SERVICE_PORT:-8888}
CLOUDKITTY_SERVICE_HOSTPORT="$CLOUDKITTY_SERVICE_HOST:$CLOUDKITTY_SERVICE_PORT"
CLOUDKITTY_SERVICE_PROTOCOL=${CLOUDKITTY_SERVICE_PROTOCOL:-$SERVICE_PROTOCOL}

# Set CloudKitty auth info
CLOUDKITTY_PRICING_USER=${CLOUDKITTY_PRICING_USER:-"admin"}
CLOUDKITTY_PRICING_PASSWORD=${CLOUDKITTY_PRICING_PASSWORD:-$ADMIN_PASSWORD}
CLOUDKITTY_PRICING_TENANT=${CLOUDKITTY_PRICING_TENANT:-"demo"}

# Set CloudKitty collect info
CLOUDKITTY_COLLECTOR=${CLOUDKITTY_COLLECTOR:-ceilometer}
CLOUDKITTY_SERVICES=${CLOUDKITTY_SERVICES:-compute}

# Set CloudKitty output info
CLOUDKITTY_OUTPUT_BACKEND=${CLOUDKITTY_OUTPUT_BACKEND:-"cloudkitty.backend.file.FileBackend"}
CLOUDKITTY_OUTPUT_BASEPATH=${CLOUDKITTY_OUTPUT_BASEPATH:-$CLOUDKITTY_REPORTS_DIR}
CLOUDKITTY_OUTPUT_PIPELINE=${CLOUDKITTY_OUTPUT_PIPELINE:-"osrf"}

# Set Cloudkitty client info
GITREPO["python-cloudkittyclient"]=${CLOUDKITTYCLIENT_REPO:-${GIT_BASE}/stackforge/python-cloudkittyclient.git}
GITDIR["python-cloudkittyclient"]=$DEST/python-cloudkittyclient
GITBRANCH["python-cloudkittyclient"]=${CLOUDKITTYCLIENT_BRANCH:-master}

# Set CloudKitty dashboard info
GITREPO["cloudkitty-dashboard"]=${CLOUDKITTYDASHBOARD_REPO:-${GIT_BASE}/stackforge/cloudkitty-dashboard.git}
GITDIR["cloudkitty-dashboard"]=$DEST/cloudkitty-dashboard
GITBRANCH["cloudkitty-dashboard"]=${CLOUDKITTYDASHBOARD_BRANCH:-master}

# Tell Tempest this project is present
TEMPEST_SERVICES+=,cloudkitty


# Functions
# ---------

# create_cloudkitty_accounts() - Set up common required cloudkitty accounts
# Tenant               User          Roles
# ------------------------------------------------------------------
# service              cloudkitty    admin        # if enabled
function create_cloudkitty_accounts {
    create_service_user "cloudkitty"

    if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then
        local cloudkitty_service=$(get_or_create_service "cloudkitty" \
            "rating" "OpenStack Rating")
        get_or_create_endpoint $cloudkitty_service \
            "$REGION_NAME" \
            "$CLOUDKITTY_SERVICE_PROTOCOL://$CLOUDKITTY_SERVICE_HOSTPORT/" \
            "$CLOUDKITTY_SERVICE_PROTOCOL://$CLOUDKITTY_SERVICE_HOSTPORT/" \
            "$CLOUDKITTY_SERVICE_PROTOCOL://$CLOUDKITTY_SERVICE_HOSTPORT/"
    fi

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
    rm -rf $CLOUDKITTY_AUTH_CACHE_DIR/*
    rm -rf $CLOUDKITTY_CONF_DIR/*
    rm -rf $CLOUDKITTY_OUTPUT_BASEPATH/*
    rm -f $CLOUDKITTY_HORIZON_ENABLED_FILE
}

# configure_cloudkitty() - Set config files, create data dirs, etc
function configure_cloudkitty {
    setup_develop $CLOUDKITTY_DIR

    sudo mkdir -m 755 -p $CLOUDKITTY_CONF_DIR
    sudo chown $STACK_USER $CLOUDKITTY_CONF_DIR

    sudo mkdir -m 755 -p $CLOUDKITTY_API_LOG_DIR
    sudo chown $STACK_USER $CLOUDKITTY_API_LOG_DIR

    cp $CLOUDKITTY_DIR$CLOUDKITTY_CONF_DIR/policy.json $CLOUDKITTY_CONF_DIR
    cp $CLOUDKITTY_DIR$CLOUDKITTY_CONF.sample $CLOUDKITTY_CONF
    iniset_rpc_backend cloudkitty $CLOUDKITTY_CONF DEFAULT

    iniset $CLOUDKITTY_CONF DEFAULT notification_topics 'notifications'
    iniset $CLOUDKITTY_CONF DEFAULT verbose True
    iniset $CLOUDKITTY_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"

    # auth
    iniset $CLOUDKITTY_CONF keystone_fetcher url "$KEYSTONE_SERVICE_PROTOCOL://$KEYSTONE_SERVICE_HOST:5000/v2.0/"
    iniset $CLOUDKITTY_CONF keystone_fetcher username cloudkitty
    iniset $CLOUDKITTY_CONF keystone_fetcher password $SERVICE_PASSWORD
    iniset $CLOUDKITTY_CONF keystone_fetcher tenant $SERVICE_TENANT_NAME
    iniset $CLOUDKITTY_CONF keystone_fetcher region $REGION_NAME

    iniset $CLOUDKITTY_CONF ceilometer_collector url "$KEYSTONE_SERVICE_PROTOCOL://$KEYSTONE_SERVICE_HOST:5000/v2.0/"
    iniset $CLOUDKITTY_CONF ceilometer_collector username cloudkitty
    iniset $CLOUDKITTY_CONF ceilometer_collector password $SERVICE_PASSWORD
    iniset $CLOUDKITTY_CONF ceilometer_collector tenant $SERVICE_TENANT_NAME
    iniset $CLOUDKITTY_CONF ceilometer_collector region $REGION_NAME

    # collect
    iniset $CLOUDKITTY_CONF collect collector $CLOUDKITTY_COLLECTOR
    iniset $CLOUDKITTY_CONF collect services $CLOUDKITTY_SERVICES

    # output
    iniset $CLOUDKITTY_CONF output backend $CLOUDKITTY_OUTPUT_BACKEND
    iniset $CLOUDKITTY_CONF output basepath $CLOUDKITTY_OUTPUT_BASEPATH
    iniset $CLOUDKITTY_CONF output pipeline $CLOUDKITTY_OUTPUT_PIPELINE

    # database
    local dburl=`database_connection_url cloudkitty`
    iniset $CLOUDKITTY_CONF database connection $dburl

    # keystone middleware
    configure_auth_token_middleware $CLOUDKITTY_CONF cloudkitty $CLOUDKITTY_AUTH_CACHE_DIR
}

# create_cloudkitty_cache_dir() - Part of the init_cloudkitty() process
function create_cloudkitty_cache_dir {
    # Create cache dir
    sudo mkdir -p $CLOUDKITTY_AUTH_CACHE_DIR/api
    sudo chown $STACK_USER $CLOUDKITTY_AUTH_CACHE_DIR/api
    rm -f $CLOUDKITTY_AUTH_CACHE_DIR/api/*
    sudo mkdir -p $CLOUDKITTY_AUTH_CACHE_DIR/registry
    sudo chown $STACK_USER $CLOUDKITTY_AUTH_CACHE_DIR/registry
    rm -f $CLOUDKITTY_AUTH_CACHE_DIR/registry/*
}

# init_cloudkitty() - Initialize CloudKitty database
function init_cloudkitty {
    # Delete existing cache
    sudo rm -rf $CLOUDKITTY_AUTH_CACHE_DIR
    sudo mkdir -p $CLOUDKITTY_AUTH_CACHE_DIR
    sudo chown $STACK_USER $CLOUDKITTY_AUTH_CACHE_DIR

    # Delete existing cache
    sudo rm -rf $CLOUDKITTY_OUTPUT_BASEPATH
    sudo mkdir -p $CLOUDKITTY_OUTPUT_BASEPATH
    sudo chown $STACK_USER $CLOUDKITTY_OUTPUT_BASEPATH

    # (Re)create cloudkitty database
    recreate_database cloudkitty utf8

    # Migrate cloudkitty database
    $CLOUDKITTY_BIN_DIR/cloudkitty-dbsync upgrade

    # Init the storage backend
    $CLOUDKITTY_BIN_DIR/cloudkitty-storage-init

    create_cloudkitty_cache_dir
}

# install_cloudkitty() - Collect source and prepare
function install_cloudkitty {
    git_clone $CLOUDKITTY_REPO $CLOUDKITTY_DIR $CLOUDKITTY_BRANCH
    setup_develop $CLOUDKITTY_DIR
}

# start_cloudkitty() - Start running processes, including screen
function start_cloudkitty {
    screen_it ck-proc "cd $CLOUDKITTY_DIR; $CLOUDKITTY_BIN_DIR/cloudkitty-processor --config-file=$CLOUDKITTY_CONF"
    screen_it ck-api "cd $CLOUDKITTY_DIR; $CLOUDKITTY_BIN_DIR/cloudkitty-api --config-file=$CLOUDKITTY_CONF"
    echo "Waiting for ck-api ($CLOUDKITTY_SERVICE_HOST:$CLOUDKITTY_SERVICE_PORT) to start..."
    if ! timeout $SERVICE_TIMEOUT sh -c "while ! wget --no-proxy -q -O- http://$CLOUDKITTY_SERVICE_HOST:$CLOUDKITTY_SERVICE_PORT; do sleep 1; done"; then
        die $LINENO "ck-api did not start"
    fi
}

# stop_cloudkitty() - Stop running processes
function stop_cloudkitty {
    # Kill the cloudkitty screen windows
    for serv in ck-api ck-proc; do
        screen_stop $serv
    done
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

# configure_cloudkitty_dashboard() - Set config files, create data dirs, etc
function configure_cloudkitty_dashboard {
    sudo ln -s  $CLOUDKITTY_ENABLED_FILE $CLOUDKITTY_HORIZON_ENABLED_FILE
    restart_apache_server
}

if is_service_enabled ck-api; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing CloudKitty"
        install_cloudkitty
        install_python_cloudkittyclient
        if is_service_enabled horizon; then
            install_cloudkitty_dashboard
        fi
        cleanup_cloudkitty
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
fi

# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
