locals {
  engineers = {
    members = [
      "engineer@acme.example.com",
    ]
    service_actions = [
      "athena:*",
      "bedrock:GetFoundationModel",
      "bedrock:InvokeModel",
      "bedrock:ListFoundationModels",
      "dynamodb:*",
      "ec2:Describe*",
      "ecr:*",
      "ecs:*",
      "glue:*",
      "iam:Get*",
      "iam:List*",
      "logs:Describe*",
      "logs:Filter*",
      "logs:Get*",
      "logs:StartQuery",
      "logs:StopQuery",
      "s3:*",
      "secretsmanager:*",
      "sns:Get*",
      "sns:List*",
      "sqs:Get*",
      "sqs:List*",
      "sqs:ReceiveMessage",
      "ssm:StartSession",
    ]
  }
  services_permissions = {
    common_actions = {
      host = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "cloudwatch:PutMetricData",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:ConditionCheckItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeStream",
        "dynamodb:DescribeTable",
        "dynamodb:GetItem",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:TransactGetItems",
        "dynamodb:TransactWriteItems",
        "dynamodb:UpdateItem",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecs:DescribeTasks",
        "ecs:RunTask",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "secretsmanager:GetSecretValue",
        "sns:Publish",
        "sqs:ChangeMessageVisibility",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage",
        "sqs:SendMessage",
        "sts:AssumeRole",
      ]
      operations = [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "secretsmanager:GetSecretValue",
      ]
    }
    individual_actions = {}
  }
  github_actions = {
    actions = {
      host = [
        "dynamodb:DescribeTable",
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:RunTask",
        "ecs:UpdateService",
        "iam:PassRole",
        "s3:GetObject",
        "s3:PutObject",
        "secretsmanager:GetSecretValue",
      ]
      feature_only = [
        "sts:AssumeRole",
      ]
      operations = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:GetAuthorizationToken",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "secretsmanager:GetSecretValue",
      ]
    }
  }
}
