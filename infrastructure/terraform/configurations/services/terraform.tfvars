# base
operations_project_id            = "acme-operations-0000"
preferred_region                 = "us-central1"
preferred_zone                   = "us-central1-b"
feature_preferred_zone           = "us-central1-a"
feature_persistence_machine_type = "e2-medium"
github_repo                      = "mention-ai-inc/app-template"

# persistence
redis_machine_type = "e2-medium"
redis_max_memory   = "3500mb"
redis_disk_size_gb = 10

# config
python_warnings = "ignore::DeprecationWarning:authlib\\._joserfc_helpers"

# api
dns_managed_zone = "acme"
domain_name      = "acme.example.com"
api_subdomain    = "api"
app_domain       = "app.acme.example.com"

services = {
  notes = {
    executors = {
      summarize_note = { timeout_seconds = 120, container_concurrency = 8 },
    },
    listeners = {
      acknowledge_command_result = {
        subscriptions = [
          {
            event_name          = "AcknowledgeCommandResult",
            source_service_name = "notes",
            topic_name          = "command_results",
          }
        ]
      },
      summarize_note = {
        subscriptions = [
          {
            event_name          = "NoteCreated",
            source_service_name = "notes",
            topic_name          = "domain_events",
          }
        ]
      },
    },
    jobs = {
      purge_notes = { schedule = "0 3 * * *" },
    },
    servers = {
      rest = {},
    },
    triggers = {
      publish_event       = { firestore_collection = "events", firestore_event_type = "written" },
      submit_command      = { firestore_collection = "commands", firestore_event_type = "written" },
      publish_audit_event = { firestore_collection = "audit", firestore_event_type = "written" }
    }
  }
}

topics = {
  command_results = {
    name = "command_results",
  }
  domain_events = {
    name                = "domain_events",
    bigquery_subscriber = true,
  }
  audit_events = {
    name                      = "audit_events",
    bigquery_subscriber       = true,
    storage_subscriber        = true,
    partition_expiration_days = 2555,
  }
}
