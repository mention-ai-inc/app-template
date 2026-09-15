locals {
  engineers = {
    members = [
      "engineer@acme.example.com",
    ]
    policy_arns = {
      host = [
        "arn:aws:iam::aws:policy/AmazonBedrockReadOnly",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser",
        "arn:aws:iam::aws:policy/AmazonECS_FullAccess",
        "arn:aws:iam::aws:policy/AmazonSQSReadOnlyAccess",
        "arn:aws:iam::aws:policy/AmazonSNSReadOnlyAccess",
        "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess",
        "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess",
        "arn:aws:iam::aws:policy/IAMReadOnlyAccess",
        "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
      ]
      feature_only = [
        "arn:aws:iam::aws:policy/AmazonAthenaFullAccess",
        "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        "arn:aws:iam::aws:policy/AmazonVPCFullAccess",
      ]
      operations = [
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
      ]
    }
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
