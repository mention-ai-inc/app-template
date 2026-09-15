data "aws_iam_policy_document" "repository" {
  count = length(concat(var.readers, var.writers)) > 0 ? 1 : 0

  dynamic "statement" {
    for_each = length(var.readers) > 0 ? [1] : []

    content {
      sid    = "Pull"
      effect = "Allow"
      actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:DescribeImages",
        "ecr:GetDownloadUrlForLayer",
      ]

      principals {
        type        = "AWS"
        identifiers = var.readers
      }
    }
  }

  dynamic "statement" {
    for_each = length(var.writers) > 0 ? [1] : []

    content {
      sid    = "Push"
      effect = "Allow"
      actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
      ]

      principals {
        type        = "AWS"
        identifiers = var.writers
      }
    }
  }
}

resource "aws_ecr_repository_policy" "repository" {
  count = length(concat(var.readers, var.writers)) > 0 ? 1 : 0

  repository = aws_ecr_repository.repository.name
  policy     = data.aws_iam_policy_document.repository[0].json
}
