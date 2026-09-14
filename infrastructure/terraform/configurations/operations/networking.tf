# shared vpc
resource "google_compute_shared_vpc_host_project" "default" {
  project = var.operations_project_id
}

resource "google_compute_shared_vpc_service_project" "default" {
  for_each = {
    production = module.production-project.project_id,
    feature    = module.feature-project.project_id
  }

  host_project    = google_compute_shared_vpc_host_project.default.project
  service_project = each.value
}

# shared network
resource "google_compute_network" "shared-vpc" {
  project                         = var.operations_project_id
  name                            = "shared-vpc"
  auto_create_subnetworks         = false
  delete_default_routes_on_create = false
  description                     = "It is expected that the vast majority of resources connect to this network, for all projects."
  mtu                             = 0
  routing_mode                    = "REGIONAL"
}

# subnetworks
resource "google_compute_subnetwork" "instances" {
  project                  = var.operations_project_id
  region                   = var.preferred_region
  name                     = "instances-subnet"
  ip_cidr_range            = var.compute_instances_ip_cidr_range
  network                  = google_compute_network.shared-vpc.id
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "cloud-run-subnet" {
  project       = var.operations_project_id
  region        = var.preferred_region
  name          = "cloud-run-subnet"
  ip_cidr_range = "172.16.0.0/12" # required: https://cloud.google.com/run/docs/configuring/shared-vpc-direct-vpc#supported-ip-ranges
  network       = google_compute_network.shared-vpc.id
}

# private services configuration for Cloud SQL
# https://cloud.google.com/sql/docs/mysql/configure-private-services-access#terraform
resource "google_compute_global_address" "private-services-connection" {
  name          = "private-services-connection"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.shared-vpc.id
}

resource "google_service_networking_connection" "service-networking-connection" {
  network                 = google_compute_network.shared-vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private-services-connection.name]
}

# cloud nat for instances subnet (allows production VMs without external IPs to reach the internet)
resource "google_compute_router" "instances" {
  project = var.operations_project_id
  region  = var.preferred_region
  name    = "instances-router"
  network = google_compute_network.shared-vpc.id
}

resource "google_compute_router_nat" "instances" {
  project = var.operations_project_id
  region  = var.preferred_region
  name    = "instances-nat"
  router  = google_compute_router.instances.name

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.instances.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

# outputs
output "shared-vpc-network-id" {
  value = google_compute_network.shared-vpc.id
}

output "cloud-run-subnetwork-id" {
  value = google_compute_subnetwork.cloud-run-subnet.id
}

output "instances-subnetwork-id" {
  value = google_compute_subnetwork.instances.id
}
