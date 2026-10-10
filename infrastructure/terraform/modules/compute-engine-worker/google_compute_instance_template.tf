resource "google_compute_instance_template" "instance-template" {
  project      = var.project_id
  region       = var.region
  machine_type = var.machine_type
  name_prefix  = substr("${var.feature_environment}${replace(var.service_name, "_", "-")}-${replace(var.worker_name, "_", "-")}", 0, 36) # max 36 characters
  description  = "Instance template for pull worker '${var.service_name}-${var.worker_name}'."

  scheduling {
    automatic_restart           = var.spot_instance ? false : true
    on_host_maintenance         = var.spot_instance ? "TERMINATE" : "MIGRATE"
    preemptible                 = var.spot_instance ? true : false
    provisioning_model          = var.spot_instance ? "SPOT" : "STANDARD"
    instance_termination_action = var.spot_instance ? "STOP" : null
  }

  service_account {
    email = var.service_account_email
    scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  network_interface {
    subnetwork = var.subnetwork

    dynamic "access_config" {
      for_each = var.needs_external_ip ? [1] : []
      content {}
    }
  }

  disk {
    auto_delete  = true
    source_image = var.disk_image
  }

  metadata = {
    gce-container-declaration    = <<-EOT
    spec:
      restartPolicy: Always
      containers:
      - name: worker
        command: ${jsonencode(var.command)}
        image: >-
          ${var.image_uri}
        env:
        - name: COMPONENT_TYPE
          value: worker
        - name: COMPONENT_NAME
          value: ${var.worker_name}
        ${join("\n    ", [for name, value in var.env : "- name: ${name}\n      value: ${value}"])}
    EOT
    google-logging-enabled       = true
    google-logging-use-fluentbit = true
    startup-script               = <<-EOT
      #! /bin/bash
      (crontab -l 2>/dev/null; echo "0 0 * * * docker restart worker") | crontab -
    EOT
  }

  lifecycle {
    create_before_destroy = true
  }
}
