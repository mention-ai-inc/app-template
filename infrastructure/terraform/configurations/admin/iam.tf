module "permissions" {
  source = "../../modules/permissions"

  services = []
}

module "task-execution-role" {
  source = "../../modules/iam-task-role"

  role_name   = "${local.feature_environment}admin-execution"
  policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
  actions     = ["secretsmanager:GetSecretValue", "kms:Decrypt"]
}

module "admin-task-role" {
  source = "../../modules/iam-task-role"

  role_name = "${local.feature_environment}admin-s"
  actions = [
    "cloudwatch:PutMetricData",
    "dynamodb:BatchGetItem",
    "dynamodb:BatchWriteItem",
    "dynamodb:DeleteItem",
    "dynamodb:DescribeTable",
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:TransactGetItems",
    "dynamodb:TransactWriteItems",
    "dynamodb:UpdateItem",
    "ecr:BatchGetImage",
    "ecr:GetDownloadUrlForLayer",
    "ecs:DescribeServices",
    "ecs:DescribeTasks",
    "ecs:ListTasks",
    "ecs:RunTask",
    "logs:CreateLogStream",
    "logs:FilterLogEvents",
    "logs:PutLogEvents",
    "s3:DeleteObject",
    "s3:GetObject",
    "s3:ListBucket",
    "s3:PutObject",
    "secretsmanager:GetSecretValue",
    "sns:Publish",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes",
    "sqs:GetQueueUrl",
    "sqs:ReceiveMessage",
    "sqs:SendMessage",
  ]
  assumable_by_user_arns = local.is_production ? [] : ["arn:aws:iam::${local.account_id}:root"]
}

data "aws_iam_policy_document" "admin-job-launching" {
  statement {
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      module.admin-task-role.arn,
      module.task-execution-role.arn,
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "admin-job-launching" {
  name   = "${local.feature_environment}admin-pass-task-roles"
  role   = module.admin-task-role.name
  policy = data.aws_iam_policy_document.admin-job-launching.json
}

data "aws_iam_policy_document" "admin-service-assumption" {
  statement {
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = values(data.terraform_remote_state.services.outputs.service_task_role_arns)
  }
}

resource "aws_iam_role_policy" "admin-service-assumption" {
  name   = "${local.feature_environment}admin-assume-services"
  role   = module.admin-task-role.name
  policy = data.aws_iam_policy_document.admin-service-assumption.json
}
