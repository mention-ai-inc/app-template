# Azure investigation access

Every environment lives in one Azure subscription, so there is no subscription to switch between —
only a resource group to name and a resource-name prefix to get right. Production is
`acme-production-0000`, every feature environment shares `acme-feature-0000`, and the registry, DNS
zone and shared secrets are in `acme-operations-0000`.

## Credentials

Engineers hold the roles `modules/permissions` grants them: Reader, Monitoring Reader, Service Bus
Data Receiver and Sender, Key Vault Secrets User and Storage Blob Data Reader everywhere, plus
Contributor, Key Vault Secrets Officer, Storage Blob Data Contributor, DocumentDB Account Contributor
and Redis Cache Contributor on the feature resource group only. Sign in with the subscription
`infrastructure/cli/provider/envrc` sets:

```bash
az login
az account show
```

There are no client secrets, and you should never create one. CI authenticates through the Entra
federated credentials in `modules/github-federation` instead, which `azure/login@v2` exchanges a
GitHub OIDC token for.

Cosmos DB data access is **not** an Azure RBAC role. It is granted separately as a Cosmos data-plane
role assignment (`azurerm_cosmosdb_sql_role_assignment`), which is why Contributor on the resource
group still cannot read a document. Applying Terraform needs the `Terraform` federated identity,
which holds Owner on the subscription.

## Reading logs

Container Apps logs land in the environment's Log Analytics workspace, and are queried with KQL:

```bash
WORKSPACE=$(az monitor log-analytics workspace show \
  --resource-group acme-feature-0000 --workspace-name acme-feature-0000-logs \
  --query customerId --output tsv)

az monitor log-analytics query --workspace "$WORKSPACE" --analytics-query "
  ContainerAppConsoleLogs_CL
  | where ContainerAppName_s == 'demonotes-p-listeners'
  | where TimeGenerated > ago(1h)
  | project TimeGenerated, Log_s
  | order by TimeGenerated desc
  | take 200"
```

`ContainerAppConsoleLogs_CL` carries what the container wrote to stdout; `ContainerAppSystemLogs_CL`
carries what the platform did to it (image pulls, probe failures, revision activation), which is where
a deploy that never came up explains itself. Structured fields the application logged are inside
`Log_s`, so `extend parsed = parse_json(Log_s) | where parsed.component_name == '...'` is how you
narrow to one handler within a pool.

`az containerapp logs show --name <app> --resource-group <rg> --follow` tails the live stream and is
the fastest way to watch a deploy land, but it reads only the running revision and keeps no history.

## Reading the document store

One database per environment, one container per service:

```bash
az cosmosdb sql container query \
  --account-name acme-feature-0000 --resource-group acme-feature-0000 \
  --database-name demoacme --name notes \
  --query-text "SELECT * FROM c WHERE c.partitionKey = '<organization id>' AND c.documentType = 'demonotes_notes'"
```

Always give `partitionKey` in the predicate. A query without one fans out across every physical
partition, costs request units on all of them, and on production is the easiest way to exhaust the
account's autoscale ceiling while learning nothing the partition-bounded query would not have told
you.

## Reaching the cache

Azure Cache for Redis has a public endpoint, TLS on port 6380, authenticated with an access key that
Terraform writes to the environment's Key Vault as `<environment>-REDIS-PASSWORD`. So unlike the other
clouds, `m list-cache-keys` works from a laptop: it reads the host from the cache resource and the key
from Key Vault, then scans over TLS. `m clear-feature-environment` flushes it the same way. Neither
will touch production — both refuse without a feature environment.
