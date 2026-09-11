resource "google_compute_instance" "cache" {
  project                   = var.project_id
  zone                      = var.zone
  machine_type              = var.machine_type
  name                      = "${var.environment_prefix}cache"
  description               = "A Redis instance intended to replace Memorystore."
  tags                      = var.is_production ? ["redis"] : ["redis", "redis-feature"]
  allow_stopping_for_update = true

  network_interface {
    subnetwork = var.subnetwork
    dynamic "access_config" {
      for_each = var.is_production ? [] : [1]
      content {}
    }
  }

  boot_disk {
    initialize_params {
      image = var.disk_image
    }
  }

  attached_disk {
    source      = google_compute_disk.redis_data.self_link
    mode        = "READ_WRITE"
    device_name = "redis-disk"
  }

  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  metadata = {
    startup-script = <<-EOT
      #!/bin/bash
      set -e

      # Install Docker
      if ! command -v docker &> /dev/null; then
        apt-get update -y
        apt-get install -y docker.io
        systemctl enable docker
        systemctl start docker
      fi

      # Format and mount the persistent disk if not already mounted
      DISK_DEVICE="/dev/disk/by-id/google-redis-disk"
      MOUNT_POINT="/mnt/stateful_partition/redis-data"

      if ! blkid $DISK_DEVICE > /dev/null 2>&1; then
        echo "Formatting Redis data disk..."
        mkfs.ext4 -F $DISK_DEVICE
      fi

      mkdir -p $MOUNT_POINT
      if ! mountpoint -q $MOUNT_POINT; then
        echo "Mounting Redis data disk..."
        mount $DISK_DEVICE $MOUNT_POINT
      fi

      # Redis runs as user 999 (redis) inside the container
      chown -R 999:999 $MOUNT_POINT
      chmod 755 $MOUNT_POINT

      # Authenticate Docker to Artifact Registry
      ACCESS_TOKEN=$(curl -s -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" \
        | tr '{,}' '\n' | grep access_token | cut -d'"' -f4)
      echo "$ACCESS_TOKEN" | docker login -u oauth2accesstoken --password-stdin us-central1-docker.pkg.dev

      # Stop and remove existing containers if they exist
      docker stop redis 2>/dev/null || true
      docker rm redis 2>/dev/null || true

      docker pull us-central1-docker.pkg.dev/${var.operations_project_id}/public-images/redis-stack-server:${var.redis_version}

      # Run Redis container with persistence configuration
      # Save snapshots:
      # - After 900 sec (15 min) if at least 1 key changed
      # - After 300 sec (5 min) if at least 10 keys changed
      # - After 60 sec if at least 10000 keys changed
      docker run -d \
        --name redis \
        --restart always \
        -p 6379:6379 \
        -v $MOUNT_POINT:/data \
        -e REDIS_ARGS="--requirepass ${var.redis_password} --maxmemory ${var.max_memory} --maxmemory-policy allkeys-lru --save 900 1 --save 300 10 --save 60 10000 --dir /data --dbfilename dump.rdb" \
        us-central1-docker.pkg.dev/${var.operations_project_id}/public-images/redis-stack-server:${var.redis_version}

      curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
      bash add-google-cloud-ops-agent-repo.sh --also-install
      mkdir -p /etc/google-cloud-ops-agent

      %{if var.is_production}
      docker pull us-central1-docker.pkg.dev/${var.operations_project_id}/public-images/redis_exporter:${var.redis_exporter_version}
      docker stop redis-exporter 2>/dev/null || true
      docker rm redis-exporter 2>/dev/null || true
      docker run -d \
        --name redis-exporter \
        --restart always \
        --network host \
        us-central1-docker.pkg.dev/${var.operations_project_id}/public-images/redis_exporter:${var.redis_exporter_version} \
        --redis.addr=redis://127.0.0.1:6379 \
        --redis.password=${var.redis_password}

      cat > /etc/google-cloud-ops-agent/config.yaml << 'OPSCONFIG'
      metrics:
        receivers:
          hostmetrics:
            type: hostmetrics
            collection_interval: 60s
          redis_prom:
            type: prometheus
            config:
              scrape_configs:
                - job_name: redis
                  scrape_interval: 60s
                  static_configs:
                    - targets: ['localhost:9121']
                  metric_relabel_configs:
                    - source_labels: [__name__]
                      regex: redis_memory_used_bytes|redis_memory_max_bytes|redis_evicted_keys_total
                      action: keep
        service:
          pipelines:
            default_pipeline:
              receivers: [hostmetrics]
            redis_pipeline:
              receivers: [redis_prom]
      OPSCONFIG
      %{else}
      docker stop redis-exporter 2>/dev/null || true
      docker rm redis-exporter 2>/dev/null || true
      rm -f /etc/google-cloud-ops-agent/config.yaml
      %{endif}

      systemctl restart google-cloud-ops-agent
    EOT
  }

  depends_on = [
    google_compute_disk.redis_data
  ]
}
