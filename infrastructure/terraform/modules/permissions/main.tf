locals {
  engineers = {
    members = [
      "engineer@acme.example.com",
    ]
    object_ids = [
      "00000000-0000-0000-0000-000000000000",
    ]
    roles = {
      host = [
        "Reader",
        "Monitoring Reader",
        "Azure Service Bus Data Receiver",
        "Azure Service Bus Data Sender",
        "Key Vault Secrets User",
        "Storage Blob Data Reader",
      ],
      feature_only = [
        "Contributor",
        "Key Vault Secrets Officer",
        "Storage Blob Data Contributor",
        "DocumentDB Account Contributor",
        "Redis Cache Contributor",
      ],
      operations = [
        "Reader",
        "AcrPull",
        "Key Vault Secrets User",
        "Storage Blob Data Contributor",
      ],
    }
  }
  services = {
    common_roles = {
      host = [
        "AcrPull",
        "Azure Service Bus Data Receiver",
        "Azure Service Bus Data Sender",
        "Key Vault Crypto User",
        "Key Vault Secrets User",
        "Monitoring Metrics Publisher",
        "Storage Blob Data Contributor",
      ]
      operations = [
        "AcrPull",
        "Key Vault Secrets User",
      ]
    }
    individual_roles = {}
  }
  github_actions = {
    roles = {
      host = [
        "Contributor",
        "Key Vault Secrets User",
        "Storage Blob Data Contributor",
      ]
      feature_only = [
        "User Access Administrator",
      ]
      operations = [
        "AcrPush",
        "Key Vault Secrets User",
      ]
    }
  }
  cosmos_data_roles = {
    reader      = "00000000-0000-0000-0000-000000000001"
    contributor = "00000000-0000-0000-0000-000000000002"
  }
}
