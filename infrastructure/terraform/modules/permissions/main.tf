locals {
  engineers = {
    members = [
      "nash@mentionai.app",
    ]
    roles = {
      host = [
        "roles/aiplatform.user",
        "roles/artifactregistry.writer",
        "roles/bigquery.dataOwner",
        "roles/bigquery.jobUser",
        "roles/iam.roleViewer",
        "roles/run.admin",
        "roles/logging.viewer",
        "roles/secretmanager.admin",
        "roles/pubsub.viewer",
        "roles/serviceusage.serviceUsageConsumer",
        "roles/cloudtasks.admin",
      ],
      feature_only = [
        "roles/bigquery.admin",
        "roles/cloudbuild.builds.editor",
        "roles/compute.admin",
        "roles/datastore.owner",
        "roles/storage.admin",
      ],
      operations = [
        "roles/artifactregistry.reader",
        "roles/aiplatform.user",
        "roles/secretmanager.secretAccessor",
        "roles/storage.objectAdmin",
      ],
    }
  }
  services = {
    common_roles = {
      host = [
        "roles/aiplatform.user",
        "roles/artifactregistry.reader",
        "roles/bigquery.dataOwner",
        "roles/cloudtasks.enqueuer",
        "roles/cloudtasks.viewer",
        "roles/compute.networkUser",
        "roles/datastore.user",
        "roles/eventarc.eventReceiver",
        "roles/logging.logWriter",
        "roles/pubsub.subscriber",
        "roles/pubsub.publisher",
        "roles/run.developer",
        "roles/run.invoker",
        "roles/secretmanager.secretAccessor",
        "roles/storage.objectAdmin",
      ]
      operations = [
        "roles/secretmanager.secretAccessor",
      ]
    }
    individual_roles = {}
  }
  github_actions = {
    roles = {
      host = [
        "roles/artifactregistry.writer",
        "roles/cloudbuild.builds.editor",
        "roles/compute.instanceAdmin.v1",
        "roles/datastore.user",
        "roles/iam.serviceAccountUser",
        "roles/run.admin",
        "roles/storage.objectAdmin",
        "roles/secretmanager.secretAccessor",
      ]
      feature_only = [
        "roles/iam.serviceAccountTokenCreator",
      ]
      operations = [
        "roles/artifactregistry.writer",
        "roles/compute.networkUser",
        "roles/secretmanager.secretAccessor",
      ]
    }
  }
}
