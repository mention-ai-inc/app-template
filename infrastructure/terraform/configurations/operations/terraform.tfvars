# base
organization_id           = "490753959095"
folder_id                 = "1043389001036"
billing_account_id        = "0187DC-31468D-8156F5"
operations_project_id     = "acme-operations-155d"
operations_project_number = "828511623120"
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
