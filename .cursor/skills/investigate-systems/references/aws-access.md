# AWS investigation access

Every environment lives in one AWS account, so there is no project to switch between — only a role to
assume and a resource-name prefix to get right.

## Credentials

Engineers belong to the `engineers` IAM group, which carries read access to CloudWatch Logs, ECS, SQS,
SNS, Glue and Athena everywhere, and full DynamoDB and S3 access outside production. Sign in with the
profile `infrastructure/cli/provider/envrc` sets:

```bash
aws sso login
aws sts get-caller-identity
```

There are no long-lived access keys, and you should never create one. CI authenticates through the
GitHub OIDC provider and the `github-actions` role instead.

Applying Terraform or creating a feature environment needs the `terraform` role, which the group may
assume:

```bash
aws sts assume-role --role-arn arn:aws:iam::000000000000:role/terraform --role-session-name investigate
```

## Reading logs

```bash
aws logs describe-log-groups --log-group-name-prefix /ecs/demo
aws logs tail /ecs/demonotes-p-listeners --since 1h --format short --follow
aws logs start-query --log-group-name /ecs/demonotes-s-rest \
  --start-time $(date -v-1H +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, component_name, @message | filter level = "ERROR" | sort @timestamp desc'
```

`aws logs tail --follow` is the fastest way to watch a deploy land. `start-query` plus
`get-query-results` is the only way to filter structured fields across many streams.

## Reading the document store

The table is `<environment>acme`. Read one document by its composite key, and a whole collection only
through the collection index:

```bash
aws dynamodb query --table-name demoacme \
  --key-condition-expression 'pk = :pk' \
  --expression-attribute-values '{":pk":{"S":"demonotes_notes#<document id>"}}'
```

Never `scan` production. A scan of a large table costs read capacity across every partition and tells
you less than the index does.

## Reaching the cache

ElastiCache has no public endpoint. Nothing on a laptop can reach it, and `m list-cache-keys` says so
rather than pretending. Use ECS Exec into a running task in the same VPC, or an SSM port forward from
an instance inside it.
