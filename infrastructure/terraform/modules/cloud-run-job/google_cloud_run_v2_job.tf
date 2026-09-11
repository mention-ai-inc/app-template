module "cloud-run-name" {
  source    = "../cloud-run-name"
  full_name = join("", [var.feature_environment, var.service_name, "-j-", replace(var.job_name, "_", "-")])
}

resource "google_cloud_run_v2_job" "cloud-run-service-job" {
  provider = google-beta

  name     = module.cloud-run-name.name
  project  = var.project_id
  location = var.region

  template {
    parallelism = var.parallelism
    task_count  = var.task_count

    template {
      service_account = var.service_account_email
      max_retries     = var.max_retries
      timeout         = var.task_timeout

      containers {
        image   = var.image_uri
        command = var.command

        env {
          name  = "COMPONENT_TYPE"
          value = "job"
        }
        env {
          name  = "COMPONENT_NAME"
          value = var.job_name
        }

        dynamic "env" {
          for_each = var.env
          content {
            name  = env.key
            value = env.value
          }
        }

        resources {
          limits = merge(
            {
              cpu    = var.cpu
              memory = var.memory
            },
            var.gpus != "0" && var.gpus != "" ? {
              "nvidia.com/gpu" = var.gpus
            } : {}
          )
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
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      labels,
      template[0].template[0].containers[0].image,
      template[0].template[0].containers[0].command,
      template[0].template[0].vpc_access,
    ]
  }

  deletion_protection = false
}
