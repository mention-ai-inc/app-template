# Redis Compute Engine Module

This Terraform module deploys a Redis cache instance on Google Compute Engine using Docker containers, following the Container-Optimized OS approach.

## Features

- **Persistent Storage**: Dedicated SSD persistent disk for Redis data with RDB snapshots
- **Docker-based Deployment**: Uses official Redis Docker images
- **LRU Eviction**: Configured with `allkeys-lru` eviction policy
- **Prometheus Monitoring**: Redis Exporter sidecar with Prometheus remote_write to Google Cloud Monitoring
- **Production-ready**: Configurable for both development and production environments
- **Auto-restart**: Containers configured with restart policy for high availability

## Architecture

The module creates:
1. A persistent SSD disk for data storage
2. A Compute Engine instance running Container-Optimized OS
3. Redis container with persistence and memory management configuration
4. Redis Exporter sidecar for Prometheus metrics
5. Prometheus sidecar for remote_write to Google Cloud Monitoring

The persistent disk is formatted on first boot and mounted to the Redis data directory, ensuring data persists across instance restarts and recreations.

## Usage

```hcl
module "redis" {
  source = "../../modules/compute-engine-redis"

  project_id            = "my-project"
  zone                  = "us-central1-b"
  subnetwork            = "projects/my-project/regions/us-central1/subnetworks/my-subnet"
  environment_prefix    = "prod-"
  service_account_email = "sa@my-project.iam.gserviceaccount.com"

  max_memory   = "2gb"
  disk_size_gb = 20
  machine_type = "e2-small"
  is_production = true
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_id | The Google Cloud project ID | string | - | yes |
| zone | The zone where the Redis instance will be deployed | string | - | yes |
| subnetwork | The subnetwork for the Redis instance | string | - | yes |
| environment_prefix | Prefix for resource naming (e.g., feature environment) | string | "" | no |
| service_account_email | Email of the service account to attach to the instance | string | - | yes |
| max_memory | The maximum memory for Redis (e.g., '900mb', '2gb') | string | - | yes |
| disk_size_gb | The size of the disk for the Redis instance | number | 10 | no |
| machine_type | The machine type of the Redis instance | string | "e2-micro" | no |
| disk_image | The disk image of the Redis instance | string | "cos-cloud/cos-stable" | no |
| is_production | Whether this is a production environment (affects external IP and tags) | bool | false | no |

## Outputs

| Name | Description |
|------|-------------|
| instance_name | The name of the Redis instance |
| instance_zone | The zone of the Redis instance |
| internal_ip | The internal IP address of the Redis instance |
| external_ip | The external IP address of the Redis instance (if assigned) |
| data_disk_name | The name of the Redis data disk |
| data_disk_size | The size of the Redis data disk in GB |

## Network Configuration

### Ports

The module exposes:
- **6379**: Redis server
- **9121**: Redis Exporter metrics (Prometheus)
- **9090**: Prometheus collector

### External Access

By default:
- **Production** (`is_production = true`): No external IP assigned, accessible only via internal network
- **Non-production** (`is_production = false`): Ephemeral external IP assigned for development access

Ensure appropriate firewall rules are configured to allow access to port 6379.

## Persistence

Redis is configured with RDB snapshot persistence:
- After 900 seconds (15 min) if at least 1 key changed
- After 300 seconds (5 min) if at least 10 keys changed
- After 60 seconds if at least 10,000 keys changed

Snapshots are stored on the persistent SSD disk mounted at `/data`.

## Memory Management

Redis is configured with:
- `maxmemory`: Set via the `max_memory` variable
- `maxmemory-policy`: `allkeys-lru` (evicts least recently used keys when memory is full)

## Machine Type Recommendations

| Use Case | Recommended Machine Type | Max Memory | Disk Size |
|----------|-------------------------|------------|-----------|
| Development/Testing | e2-micro (2 vCPU, 1 GB) | 900mb | 10 GB |
| Small Production | e2-small (2 vCPU, 2 GB) | 1500mb | 20 GB |
| Medium Production | e2-medium (2 vCPU, 4 GB) | 3gb | 50 GB |
| Large Production | e2-standard-2 (2 vCPU, 8 GB) | 6gb | 100 GB |

## Monitoring

The instance runs three containers:
- **redis**: The Redis server
- **redis-exporter**: Exports Redis metrics in Prometheus format on port 9121
- **prometheus**: Scrapes redis-exporter and remote_writes to Google Cloud Monitoring

Metrics are available in Google Cloud Monitoring under Prometheus with the `redis` job label.

## Dependencies

- Google Cloud Project with Compute Engine API enabled
- Container-Optimized OS supports Docker by default
- Network configuration (VPC, subnetwork) must exist
- Service account with `roles/monitoring.metricWriter` for Prometheus remote_write
