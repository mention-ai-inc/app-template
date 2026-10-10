subscription_id                = "00000000-0000-0000-0000-000000000000"
tenant_id                      = "00000000-0000-0000-0000-000000000000"
operations_resource_group_name = "acme-operations-0000"
preferred_region               = "eastus"
github_repo                    = "mention-ai-inc/app-template"

cosmos_max_throughput       = 4000
cosmos_lease_max_throughput = 1000
redis_sku_name              = "Standard"
redis_family                = "C"
redis_capacity              = 1
feature_redis_sku_name      = "Basic"
feature_redis_family        = "C"
feature_redis_capacity      = 0

python_warnings = "ignore::DeprecationWarning:authlib\\._joserfc_helpers"

domain_name   = "acme.example.com"
api_subdomain = "api"
app_domain    = "app.acme.example.com"

services = {
  notes = {
    executor_pools = {
      standard = { timeout_seconds = 120, container_concurrency = 8 },
    },
    executors = {
      summarize_note = { pool = "standard" },
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
      publish_event       = { document_type = "events" },
      submit_command      = { document_type = "commands" },
      publish_audit_event = { document_type = "audit" }
    }
  }
}

topics = {
  command_results = {
    name = "command_results",
  }
  domain_events = {
    name    = "domain_events",
    archive = true,
  }
  audit_events = {
    name    = "audit_events",
    archive = true,
  }
}
