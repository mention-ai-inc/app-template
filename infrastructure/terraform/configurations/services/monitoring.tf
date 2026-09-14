resource "google_bigquery_dataset" "api_logs" {
  project       = local.project
  dataset_id    = "${local.feature_environment}api_logs"
  friendly_name = "API Logs"
  description   = "Cloud Run API request and response logs for analytics and monitoring"
  location      = "US"

  delete_contents_on_destroy = true

  labels = {
    environment = local.feature_environment != "" ? local.feature_environment : "production"
    purpose     = "api-monitoring"
  }
}

resource "google_bigquery_dataset_iam_member" "terraform_owner" {
  project    = local.project
  dataset_id = google_bigquery_dataset.api_logs.dataset_id
  role       = "roles/bigquery.dataOwner"
  member     = "serviceAccount:terraform@${var.operations_project_id}.iam.gserviceaccount.com"
}

resource "google_bigquery_dataset_iam_member" "engineers_owners" {
  for_each   = local.is_production ? toset([]) : toset(module.permissions.engineers_members)
  project    = local.project
  dataset_id = google_bigquery_dataset.api_logs.dataset_id
  role       = "roles/bigquery.dataOwner"
  member     = "user:${each.value}"
}

resource "google_logging_project_sink" "api_logs_sink" {
  project = local.project
  name    = "${local.feature_environment}api-logs-to-bigquery"

  destination = "bigquery.googleapis.com/projects/${local.project}/datasets/${google_bigquery_dataset.api_logs.dataset_id}"

  filter = <<-EOT
    resource.type="cloud_run_revision"
    AND jsonPayload.logType="custom"
  EOT

  unique_writer_identity = true
}

resource "google_bigquery_dataset_iam_member" "logs_sink_writer" {
  project    = local.project
  dataset_id = google_bigquery_dataset.api_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.api_logs_sink.writer_identity
}

# alerting

resource "google_monitoring_notification_channel" "engineering_alert_email" {
  project      = local.project
  display_name = "Engineering Alerts"
  type         = "email"
  labels = {
    email_address = "engineering@acme.example.com"
  }
}

resource "google_monitoring_alert_policy" "redis_memory_pressure" {
  count = local.is_production ? 1 : 0

  project      = local.project
  display_name = "Redis Memory Pressure"
  combiner     = "OR"

  conditions {
    display_name = "Redis memory usage above 85% of maxmemory"
    condition_prometheus_query_language {
      query               = <<-EOT
        redis_memory_used_bytes{job="redis"} / redis_memory_max_bytes{job="redis"} > 0.85
      EOT
      duration            = "300s"
      evaluation_interval = "60s"
    }
  }

  notification_channels = [google_monitoring_notification_channel.engineering_alert_email.name]

  documentation {
    subject = "Redis approaching memory limit"
    content = "Redis memory usage has exceeded 85% of the configured maxmemory. Consider upgrading redis_machine_type and redis_max_memory."
  }
}

resource "google_monitoring_alert_policy" "redis_evictions" {
  count = local.is_production ? 1 : 0

  project      = local.project
  display_name = "Redis Key Evictions"
  combiner     = "OR"

  conditions {
    display_name = "Redis is evicting keys"
    condition_prometheus_query_language {
      query               = <<-EOT
        increase(redis_evicted_keys_total{job="redis"}[5m]) > 0
      EOT
      duration            = "0s"
      evaluation_interval = "60s"
    }
  }

  notification_channels = [google_monitoring_notification_channel.engineering_alert_email.name]

  documentation {
    subject = "Redis is evicting keys"
    content = "Redis has started evicting keys due to memory pressure. Data is being lost. Upgrade redis_machine_type and redis_max_memory immediately."
  }
}

resource "google_monitoring_alert_policy" "vm_high_cpu" {
  for_each = toset(["${local.feature_environment}cache"])

  project      = local.project
  display_name = "${each.value} High CPU"
  combiner     = "OR"

  conditions {
    display_name = "CPU utilization above 80% for 5 minutes"
    condition_threshold {
      filter          = "resource.type=\"gce_instance\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\" AND metadata.system_labels.name=\"${each.value}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.engineering_alert_email.name]

  documentation {
    subject = "${each.value} CPU utilization high"
    content = "Instance ${each.value} has sustained CPU utilization above 80% for 5 minutes. Consider upgrading the machine type."
  }
}
