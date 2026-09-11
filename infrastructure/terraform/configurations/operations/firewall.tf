resource "google_compute_firewall" "cloud-ssh" {
  # metadata
  name        = "cloud-ssh"
  description = "Rule enabling users to SSH into instances from the GCP console."

  # network
  network = google_compute_network.shared-vpc.name

  # ports
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # sources and targets
  source_ranges      = ["35.235.240.0/20"]
  destination_ranges = [var.compute_instances_ip_cidr_range]
}

resource "google_compute_firewall" "redis" {
  # metadata
  name        = "redis"
  description = "Rule enabling access to Redis from other instances."

  # network
  network = google_compute_network.shared-vpc.name

  # ports
  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  # sources and targets
  source_ranges = [
    google_compute_subnetwork.cloud-run-subnet.ip_cidr_range,
    google_compute_subnetwork.instances.ip_cidr_range,
  ]
  target_tags = ["redis"]
}

resource "google_compute_firewall" "redis-feature" {
  # metadata  
  name        = "redis-feature"
  description = "Rule enabling access to Redis from the public internet in feature environments (protected by Redis AUTH)."

  # network
  network = google_compute_network.shared-vpc.name

  # ports
  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  # sources and targets
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["redis-feature"]
}
