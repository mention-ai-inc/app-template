module "cloud-run-name" {
  source    = "../cloud-run-name"
  full_name = join("", [var.feature_environment, var.service_name, "-p-", replace(var.pool_name, "_", "-")])
}

resource "google_cloud_run_v2_service" "pool" {
  provider = google-beta

  name     = module.cloud-run-name.name
  project  = var.project_id
  location = var.region

  template {
    service_account                  = var.service_account_email
    max_instance_request_concurrency = var.container_concurrency
    timeout                          = "${var.timeout_seconds}s"

    containers {
      image   = var.image_uri
      command = var.command

      env {
        name  = "COMPONENT_TYPE"
        value = var.component_type
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true
      }
    }

    dynamic "vpc_access" {
      for_each = var.vpc_network != "" ? [1] : []

      content {
        egress = "PRIVATE_RANGES_ONLY" # otherwise all traffic goes through the VPC and we effectively lose internet access

        network_interfaces {
          network    = var.vpc_network
          subnetwork = var.vpc_subnetwork
        }
      }
    }

    scaling {
      min_instance_count = var.minimum_instances
      max_instance_count = var.maximum_instances
    }

  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      labels,
      scaling,
      template[0].containers[0].image,
      template[0].containers[0].command,
      template[0].labels,
      template[0].revision,
      template[0].vpc_access,
    ]
  }

  deletion_protection = false
}
