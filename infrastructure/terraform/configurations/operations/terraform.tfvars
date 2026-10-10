# base
organization_id           = "000000000000"
folder_id                 = "000000000000"
billing_account_id        = "000000-000000-000000"
operations_project_id     = "acme-operations-0000"
operations_project_number = "000000000000"
github_repo               = "mention-ai-inc/app-template"
gcp_services = [
  "aiplatform.googleapis.com",
  "artifactregistry.googleapis.com",
  "bigquery.googleapis.com",
  "certificatemanager.googleapis.com",
  "cloudbuild.googleapis.com",
  "cloudscheduler.googleapis.com",
  "cloudtasks.googleapis.com",
  "compute.googleapis.com",
  "dns.googleapis.com",
  "domains.googleapis.com",
  "eventarc.googleapis.com",
  "firestore.googleapis.com",
  "iam.googleapis.com",
  "iap.googleapis.com",
  "iamcredentials.googleapis.com",
  "monitoring.googleapis.com",
  "pubsub.googleapis.com",
  "run.googleapis.com",
  "secretmanager.googleapis.com",
  "servicenetworking.googleapis.com",
  "vpcaccess.googleapis.com",
]
preferred_region = "us-central1"

# networking
compute_instances_ip_cidr_range = "10.0.0.0/24"
