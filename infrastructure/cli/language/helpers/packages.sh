service_packages() {
    local manifest
    for manifest in services/*/pyproject.toml; do
        [ -e "$manifest" ] || continue
        dirname "$manifest"
    done
}

language_packages() {
    echo library
    echo backfills
    service_packages
}
