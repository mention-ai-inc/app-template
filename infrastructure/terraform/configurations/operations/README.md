# Operations

This document outlines the manual steps required to create the Azure operations estate such that its
configuration can be successfully applied with a `terraform apply`.

## Initial creation

1. Create the subscription that every environment lives in, and note its ID and tenant ID.
1. Create a resource group named `acme-operations-0000` in `eastus`.
1. Create a storage account named `acmeoperations0000tf` in that resource group.
   - Enable blob versioning, and keep 7 versions.
   - Disable shared key access, so that the backend authenticates with Entra ID only.
1. Create a blob container in it named `terraform-state`.

Terraform manages everything else, including the production and feature resource groups. The
operations resource group is read as a data source rather than managed, because it holds the state
account that Terraform itself reads from.

## Terraform identity setup

1. Grant whoever applies Terraform `Owner` and `Storage Blob Data Contributor` on the subscription.
   - `Owner` rather than `Contributor`, because the configuration creates role assignments.
   - Keep it for as long as they create feature environments or apply Terraform locally;
     `m create-feature-environment` and `m terraform-*` sign in as this principal. Production ships
     through GitHub Actions against the federated `Terraform` application this configuration creates.
1. After the first apply, take the `terraform_client_id` output and set it as the `client-id` the
   production workflow passes to `azure/login`.

## Register resource providers

Some resource providers must be registered on the subscription before an apply succeeds:

- Microsoft.App
- Microsoft.ContainerRegistry
- Microsoft.DocumentDB
- Microsoft.KeyVault
- Microsoft.ManagedIdentity
- Microsoft.Network
- Microsoft.OperationalInsights
- Microsoft.ServiceBus
- Microsoft.Storage
- Microsoft.Cache

## Secrets

The configuration creates the three key vaults but not the secrets in them, because their values come
from third parties. Add these by hand before applying `services`, `mcp`, or `admin`:

| Vault | Secret |
| --- | --- |
| operations | `SENTRY-DSN` |
| production, feature | `CLERK-SECRET-KEY`, `CLERK-WEBHOOK-SECRET`, `GEMINI-API-KEY`, `LOGFIRE-WRITE-TOKEN` |
| operations | `VERCEL-TERRAFORM-API-KEY` |

Key Vault secret names admit only letters, digits, and hyphens, so the environment variable names the
application reads are spelled with hyphens here and translated back by the configurations.
