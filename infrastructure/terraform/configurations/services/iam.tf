module "permissions" {
  source = "../../modules/permissions"

  services = keys(var.services)
}

module "task-execution-role" {
  source = "../../modules/iam-task-role"

  role_name   = "${local.feature_environment}services-execution"
  policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
  actions = [
    "secretsmanager:GetSecretValue",
    "kms:Decrypt",
  ]
}

module "service-task-role" {
  source   = "../../modules/iam-task-role"
  for_each = toset(keys(var.services))

  role_name = "${local.feature_environment}${each.value}-s"
  actions = concat(
    module.permissions.service_actions.host[each.value],
    module.permissions.service_actions.operations[each.value],
  )
  assumable_by_user_arns = ["arn:aws:iam::${local.account_id}:root"]
}

resource "aws_iam_role_policy" "cross-service-assumption" {
  for_each = length(var.services) > 1 ? toset(keys(var.services)) : toset([])

  name = "${local.feature_environment}${each.value}-assume-siblings"
  role = module.service-task-role[each.value].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = [for service, role in module.service-task-role : role.arn if service != each.value]
      },
    ]
  })
}

module "default-task-role" {
  source = "../../modules/iam-task-role"

  role_name   = "${local.feature_environment}default"
  policy_arns = ["arn:aws:iam::aws:policy/ReadOnlyAccess"]
}

output "service_task_role_arns" {
  description = "ARNs of the per-service task roles, keyed by service name."
  value       = { for service, role in module.service-task-role : service => role.arn }
}

output "task_execution_role_arn" {
  description = "ARN of the role the ECS agent pulls images and reads secrets as."
  value       = module.task-execution-role.arn
}
