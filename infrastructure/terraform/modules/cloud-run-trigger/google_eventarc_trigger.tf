resource "google_eventarc_trigger" "firestore_trigger" {
  name     = join("", [var.feature_environment, var.service_name, "-", replace(var.trigger_name, "_", "-"), "-trigger"])
  location = var.region
  project  = var.project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.firestore.document.v1.${var.firestore_event_type}"
  }

  matching_criteria {
    attribute = "database"
    value     = "(default)"
  }

  matching_criteria {
    attribute = "namespace"
    value     = "(default)"
  }

  matching_criteria {
    attribute = "document"
    value     = "${var.feature_environment}${var.service_name}_${var.firestore_collection}/{document_id=**}"
    operator  = "match-path-pattern"
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.trigger.name
      region  = var.region
    }
  }

  event_data_content_type = "application/protobuf"
  service_account = var.service_account_email
} 