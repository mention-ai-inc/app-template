preferred_region = "us-east-1"
github_repo      = "mention-ai-inc/app-template"

redis_node_type         = "cache.t4g.small"
feature_redis_node_type = "cache.t4g.micro"
redis_engine_version    = "7.1"

python_warnings = "ignore::DeprecationWarning:authlib\\._joserfc_helpers"
alert_email     = "engineer@acme.example.com"

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
      purge_notes = { schedule = "cron(0 3 * * ? *)" },
    },
    servers = {
      rest = {},
    },
    triggers = {
      publish_event       = { collection = "events" },
      submit_command      = { collection = "commands" },
      publish_audit_event = { collection = "audit" }
    }
  }
}

topics = {
  command_results = {
    name = "command_results",
  }
  domain_events = {
    name                 = "domain_events",
    archive_subscriber   = true,
    analytics_subscriber = true,
  }
  audit_events = {
    name                 = "audit_events",
    archive_subscriber   = true,
    analytics_subscriber = true,
  }
}
