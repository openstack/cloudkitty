# cloudkitty.sh - Devstack extras script to install CloudKitty

if is_service_enabled ck-api; then
    if [[ "$1" == "source" ]]; then
        # Initial source
        source $TOP_DIR/lib/cloudkitty
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing CloudKitty"
        install_cloudkitty
        install_python_cloudkittyclient
        cleanup_cloudkitty
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring CloudKitty"
        configure_cloudkitty

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
